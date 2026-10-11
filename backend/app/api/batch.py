from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any, Optional
import uuid
import csv
import json
import io
import logging
from datetime import datetime

from app.database import get_db
from app.schemas import (
    BatchAnalyzeRequest,
    BatchAnalyzeResponse,
    BatchRunResponse,
    DecisionEnum,
    ThreatTypeEnum,
)
from app.models import EvaluationRun
from app.waf.gateway import get_waf_gateway
from app.schemas import WAFInspectRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/batch", tags=["Batch Analysis"])

# In-memory storage for batch runs
batch_runs: Dict[str, Dict[str, Any]] = {}


@router.post("/analyze", response_model=BatchAnalyzeResponse)
async def analyze_batch(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    has_labels: bool = Form(False),
):
    """Analyze a batch of requests from CSV/JSON file."""
    run_id = str(uuid.uuid4())[:12]

    # Read file content
    content = await file.read()
    text = content.decode("utf-8")

    # Parse based on file type
    if file.filename.endswith(".csv"):
        requests = _parse_csv(text, has_labels)
    elif file.filename.endswith(".json"):
        requests = _parse_json(text, has_labels)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type. Use CSV or JSON.")

    if not requests:
        raise HTTPException(status_code=400, detail="No valid requests found in file.")

    # Initialize run
    batch_runs[run_id] = {
        "run_id": run_id,
        "dataset_name": file.filename,
        "status": "running",
        "started_at": datetime.utcnow().isoformat(),
        "total_samples": len(requests),
        "processed": 0,
        "threats_detected": 0,
        "blocked": 0,
        "allowed": 0,
        "results": [],
        "ground_truth": [r.get("label") for r in requests] if has_labels else None,
    }

    # Run in background
    background_tasks.add_task(_execute_batch_analysis, run_id, requests, has_labels)

    return BatchAnalyzeResponse(
        run_id=run_id,
        status="running",
        total_samples=len(requests),
        processed=0,
        threats_detected=0,
        blocked=0,
        allowed=0,
        precision=None,
        recall=None,
        f1=None,
        false_positive_rate=None,
    )


async def _execute_batch_analysis(
    run_id: str,
    requests: List[Dict[str, Any]],
    has_labels: bool,
):
    """Execute batch analysis in background."""
    waf = await get_waf_gateway()
    run = batch_runs[run_id]

    y_true = []
    y_pred = []

    for i, req_data in enumerate(requests):
        try:
            request = WAFInspectRequest(
                method=req_data.get("method", "GET"),
                path=req_data.get("path", "/"),
                query=req_data.get("query", ""),
                headers=req_data.get("headers", {}),
                body=req_data.get("body", ""),
                source_ip=req_data.get("source_ip", "127.0.0.1"),
                session_id=req_data.get("session_id"),
                user_id=req_data.get("user_id"),
            )

            decision = await waf.inspect(request)

            result = {
                "index": i,
                "request_id": decision.request_id,
                "method": request.method,
                "path": request.path,
                "risk_score": decision.risk_score,
                "attack_type": decision.attack_type.value if decision.attack_type else None,
                "decision": decision.decision.value,
                "latency_ms": decision.latency_ms,
            }

            if has_labels and "label" in req_data:
                result["ground_truth"] = req_data["label"]
                y_true.append(req_data["label"])
                y_pred.append(decision.attack_type.value if decision.attack_type else "benign")

            run["results"].append(result)
            run["processed"] += 1

            if decision.attack_type and decision.attack_type != ThreatTypeEnum.BENIGN:
                run["threats_detected"] += 1

            if decision.decision == DecisionEnum.BLOCK:
                run["blocked"] += 1
            else:
                run["allowed"] += 1

        except Exception as e:
            logger.error(f"Batch analysis error for request {i}: {e}")
            run["results"].append({
                "index": i,
                "error": str(e),
            })

    # Calculate metrics if labels available
    if has_labels and y_true and y_pred:
        from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
        try:
            # Convert to binary (benign vs malicious)
            y_true_bin = [0 if l == "benign" else 1 for l in y_true]
            y_pred_bin = [0 if l == "benign" else 1 for l in y_pred]

            precision = precision_score(y_true_bin, y_pred_bin, zero_division=0)
            recall = recall_score(y_true_bin, y_pred_bin, zero_division=0)
            f1 = f1_score(y_true_bin, y_pred_bin, zero_division=0)

            cm = confusion_matrix(y_true_bin, y_pred_bin)
            tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, 0)
            fpr = fp / (fp + tn) if (fp + tn) > 0 else 0

            run["precision"] = round(precision, 4)
            run["recall"] = round(recall, 4)
            run["f1"] = round(f1, 4)
            run["false_positive_rate"] = round(fpr, 4)
        except Exception as e:
            logger.error(f"Metrics calculation error: {e}")

    run["status"] = "completed"
    run["completed_at"] = datetime.utcnow().isoformat()

    # Persist to database
    try:
        from app.database import get_db_context
        async with get_db_context() as db:
            eval_run = EvaluationRun(
                run_name=run_id,
                dataset_name=run["dataset_name"],
                started_at=datetime.fromisoformat(run["started_at"]),
                completed_at=datetime.utcnow(),
                total_samples=run["total_samples"],
                precision=run.get("precision"),
                recall=run.get("recall"),
                f1=run.get("f1"),
                false_positive_rate=run.get("false_positive_rate"),
            )
            db.add(eval_run)
            await db.commit()
    except Exception as e:
        logger.error(f"Failed to persist batch run: {e}")


def _parse_csv(text: str, has_labels: bool) -> List[Dict[str, Any]]:
    """Parse CSV file to request list."""
    requests = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        headers_dict = {}
        raw_headers = row.get("headers")
        if raw_headers and raw_headers.strip():
            try:
                parsed = json.loads(raw_headers.strip())
                if isinstance(parsed, dict):
                    headers_dict = parsed
            except Exception:
                headers_dict = {}

        req = {
            "method": row.get("method", "GET") or "GET",
            "path": row.get("path", "/") or "/",
            "query": row.get("query", "") or "",
            "headers": headers_dict,
            "body": row.get("body", "") or "",
            "source_ip": row.get("source_ip", "127.0.0.1") or "127.0.0.1",
            "session_id": row.get("session_id"),
            "user_id": row.get("user_id"),
        }
        if has_labels and "label" in row:
            req["label"] = row["label"]
        requests.append(req)
    return requests


def _parse_json(text: str, has_labels: bool) -> List[Dict[str, Any]]:
    """Parse JSON file to request list."""
    try:
        data = json.loads(text)
    except Exception:
        return []
    if isinstance(data, dict) and "requests" in data:
        return data["requests"]
    elif isinstance(data, list):
        return data
    return []


@router.get("/runs/{run_id}", response_model=BatchRunResponse)
async def get_batch_run(run_id: str):
    """Get batch analysis run results."""
    if run_id not in batch_runs:
        raise HTTPException(status_code=404, detail="Run not found")

    run = batch_runs[run_id]
    return BatchRunResponse(
        id=run["run_id"],
        run_name=run_id,
        dataset_name=run["dataset_name"],
        status=run["status"],
        started_at=datetime.fromisoformat(run["started_at"]),
        completed_at=datetime.fromisoformat(run["completed_at"]) if run.get("completed_at") else None,
        total_samples=run["total_samples"],
        results=run.get("results"),
        precision=run.get("precision"),
        recall=run.get("recall"),
        f1=run.get("f1"),
        false_positive_rate=run.get("false_positive_rate"),
    )


@router.get("/runs")
async def list_batch_runs():
    """List all batch analysis runs."""
    return [
        {
            "run_id": run["run_id"],
            "dataset_name": run["dataset_name"],
            "status": run["status"],
            "started_at": run["started_at"],
            "completed_at": run.get("completed_at"),
            "total_samples": run["total_samples"],
            "processed": run["processed"],
            "threats_detected": run["threats_detected"],
            "blocked": run["blocked"],
            "allowed": run["allowed"],
            "precision": run.get("precision"),
            "recall": run.get("recall"),
            "f1": run.get("f1"),
        }
        for run in batch_runs.values()
    ]


@router.post("/runs/{run_id}/export")
async def export_batch_results(run_id: str, format: str = "json"):
    """Export batch analysis results."""
    if run_id not in batch_runs:
        raise HTTPException(status_code=404, detail="Run not found")

    run = batch_runs[run_id]

    if format == "csv":
        import io
        output = io.StringIO()
        if run["results"]:
            writer = csv.DictWriter(output, fieldnames=run["results"][0].keys())
            writer.writeheader()
            writer.writerows(run["results"])
        return {"content": output.getvalue(), "filename": f"{run_id}_results.csv", "content_type": "text/csv"}
    else:
        return {"content": json.dumps(run["results"], indent=2), "filename": f"{run_id}_results.json", "content_type": "application/json"}