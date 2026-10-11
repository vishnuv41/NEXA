from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any, Optional
import uuid
import logging
import asyncio
from datetime import datetime

from app.database import get_db
from app.schemas import (
    AttackLabRunRequest,
    AttackLabRunResponse,
    AttackVariantResult,
    DecisionEnum,
    ThreatTypeEnum,
)
from app.models import AttackCampaign
from app.attacks.generator import AttackVariantGenerator
from app.waf.gateway import get_waf_gateway, WAFGateway
from app.schemas import WAFInspectRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/attack-lab", tags=["Attack Lab"])

# In-memory storage for attack lab runs (in production, use Redis/DB)
attack_lab_runs: Dict[str, Dict[str, Any]] = {}


@router.post("/run", response_model=AttackLabRunResponse)
async def run_attack_lab(
    request: AttackLabRunRequest,
    waf: WAFGateway = Depends(get_waf_gateway),
):
    """Run attack lab robustness test."""
    run_id = str(uuid.uuid4())[:12]

    # Initialize run record
    attack_lab_runs[run_id] = {
        "run_id": run_id,
        "attack_family": request.attack_family,
        "status": "running",
        "started_at": datetime.utcnow().isoformat(),
        "total_variants": request.variant_count,
        "variants": [],
        "detected": 0,
        "missed": 0,
    }

    # Execute test
    await _execute_attack_lab(run_id, request, waf)

    run = attack_lab_runs[run_id]
    variants = [AttackVariantResult(**v) for v in run.get("variants", [])]

    return AttackLabRunResponse(
        run_id=run_id,
        attack_family=request.attack_family,
        total_variants=run.get("total_variants", len(variants)),
        detected=run.get("detected", 0),
        missed=run.get("missed", 0),
        detection_rate=run.get("detection_rate", 0.0),
        avg_latency_ms=run.get("avg_latency_ms", 0.0),
        variants=variants,
    )


async def _execute_attack_lab(
    run_id: str,
    request: AttackLabRunRequest,
    waf: WAFGateway,
):
    """Execute attack lab test in background."""
    generator = AttackVariantGenerator()
    
    # Generate variants
    base_payloads = request.base_payloads or generator.get_default_payloads(request.attack_family)
    variants = generator.generate_variants(
        base_payloads,
        request.attack_family,
        request.variant_count,
    )

    run = attack_lab_runs[run_id]
    run["variants"] = []

    detected = 0
    total_latency = 0

    for variant in variants:
        # Test against WAF
        test_request = WAFInspectRequest(
            method="GET",
            path=request.target_endpoint,
            query=f"q={variant['payload']}",
            headers={"user-agent": "AttackLab/1.0"},
            body="",
            source_ip="127.0.0.1",
            session_id=f"attack-lab-{run_id}",
        )

        try:
            decision = await waf.inspect(test_request)
            
            is_detected = decision.decision in [DecisionEnum.BLOCK, DecisionEnum.CHALLENGE, DecisionEnum.RATE_LIMIT]
            if is_detected:
                detected += 1

            total_latency += decision.latency_ms

            variant_result = AttackVariantResult(
                variant=variant["payload"],
                original=variant["original"],
                transformations=variant["transformations"],
                detected=is_detected,
                risk_score=decision.risk_score,
                decision=decision.decision,
                attack_type=decision.attack_type,
                latency_ms=decision.latency_ms,
            )

            run["variants"].append(variant_result.model_dump())
            run["detected"] = detected
            run["missed"] = len(run["variants"]) - detected

        except Exception as e:
            logger.error(f"Attack lab variant test error: {e}")

    run["status"] = "completed"
    run["completed_at"] = datetime.utcnow().isoformat()
    run["detection_rate"] = detected / len(variants) if variants else 0
    run["avg_latency_ms"] = total_latency / len(variants) if variants else 0


@router.get("/runs/{run_id}", response_model=AttackLabRunResponse)
async def get_attack_lab_run(run_id: str):
    """Get attack lab run results."""
    if run_id not in attack_lab_runs:
        raise HTTPException(status_code=404, detail="Run not found")

    run = attack_lab_runs[run_id]
    variants = [AttackVariantResult(**v) for v in run.get("variants", [])]

    return AttackLabRunResponse(
        run_id=run["run_id"],
        attack_family=run["attack_family"],
        total_variants=run["total_variants"],
        detected=run["detected"],
        missed=run["missed"],
        detection_rate=run.get("detection_rate", 0),
        avg_latency_ms=run.get("avg_latency_ms", 0),
        variants=variants,
    )


@router.get("/runs")
async def list_attack_lab_runs():
    """List all attack lab runs."""
    return [
        {
            "run_id": run["run_id"],
            "attack_family": run["attack_family"],
            "status": run["status"],
            "started_at": run["started_at"],
            "completed_at": run.get("completed_at"),
            "total_variants": run["total_variants"],
            "detected": run["detected"],
            "missed": run["missed"],
            "detection_rate": run.get("detection_rate", 0),
        }
        for run in attack_lab_runs.values()
    ]


@router.get("/payloads/families")
async def get_attack_families():
    """Get available attack families and default payloads."""
    generator = AttackVariantGenerator()
    return {
        "families": [
            {
                "id": "sql_injection",
                "name": "SQL Injection",
                "description": "SQL injection attack variants",
                "default_payloads": generator.get_default_payloads("sql_injection")[:5],
            },
            {
                "id": "xss",
                "name": "Cross-Site Scripting (XSS)",
                "description": "XSS attack variants",
                "default_payloads": generator.get_default_payloads("xss")[:5],
            },
            {
                "id": "path_traversal",
                "name": "Path Traversal",
                "description": "Directory traversal variants",
                "default_payloads": generator.get_default_payloads("path_traversal")[:5],
            },
            {
                "id": "command_injection",
                "name": "Command Injection",
                "description": "OS command injection variants",
                "default_payloads": generator.get_default_payloads("command_injection")[:5],
            },
            {
                "id": "mixed",
                "name": "Mixed (All Families)",
                "description": "Combined attack variants from all families",
                "default_payloads": [],
            },
        ]
    }