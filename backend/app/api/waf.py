from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List, Optional
import logging
import json

from app.database import get_db
from app.schemas import (
    WAFInspectRequest,
    WAFInspectResponse,
    RequestEventResponse,
    DecisionEnum,
    WAFModeEnum,
    PolicyUpdateRequest,
    PolicyResponse,
    RiskThresholds,
    RiskWeights,
    FeedbackRequest,
    FeedbackResponse,
    HealthResponse,
)
from app.models import RequestEvent, ThreatEvent, AnalystFeedback, DecisionEnum as ModelDecisionEnum, ThreatTypeEnum
from app.waf.gateway import get_waf_gateway, WAFGateway
from app.risk.engine import get_risk_engine
from app.streaming.events import get_sse_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/waf", tags=["WAF"])


@router.post("/inspect", response_model=WAFInspectResponse)
async def inspect_request(
    request: WAFInspectRequest,
    waf: WAFGateway = Depends(get_waf_gateway),
):
    """Inspect a request through the WAF pipeline."""
    try:
        decision = await waf.inspect(request)
        return WAFInspectResponse(
            request_id=decision.request_id,
            decision=decision.decision,
            risk_score=decision.risk_score,
            attack_type=decision.attack_type,
            transformer_score=decision.transformer_score,
            anomaly_score=decision.anomaly_score,
            session_score=decision.session_score,
            application_score=decision.application_score,
            rule_score=decision.rule_score,
            reasons=decision.reasons,
            signals=decision.signals,
            latency_ms=decision.latency_ms,
            timestamp=decision.explanation.evidence[0].raw_data.get("timestamp") if decision.explanation and decision.explanation.evidence else None,
        )
    except Exception as e:
        logger.error(f"WAF inspect error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/inspect-and-proxy")
async def inspect_and_proxy(
    request: WAFInspectRequest,
    waf: WAFGateway = Depends(get_waf_gateway),
):
    """Inspect request and proxy to demo app if allowed."""
    decision = await waf.inspect(request)

    # In shadow mode, always allow through
    if decision.decision == DecisionEnum.BLOCK:
        return {
            "request_id": decision.request_id,
            "decision": decision.decision.value,
            "risk_score": decision.risk_score,
            "attack_type": decision.attack_type.value if decision.attack_type else None,
            "blocked": True,
            "message": "Request blocked by WAF",
        }

    # Proxy to demo app
    try:
        response = await waf.proxy_request(request)
        return {
            "request_id": decision.request_id,
            "decision": decision.decision.value,
            "risk_score": decision.risk_score,
            "attack_type": decision.attack_type.value if decision.attack_type else None,
            "blocked": False,
            "upstream_status": response.status_code,
            "upstream_body": response.text[:5000],
        }
    except Exception as e:
        logger.error(f"Proxy error: {e}")
        return {
            "request_id": decision.request_id,
            "decision": decision.decision.value,
            "risk_score": decision.risk_score,
            "error": "Failed to proxy to demo application",
        }


@router.get("/mode")
async def get_mode():
    """Get current WAF mode."""
    engine = get_risk_engine()
    return {"mode": engine.mode.value}


@router.post("/mode")
async def set_mode(request: Request, mode: Optional[WAFModeEnum] = None):
    """Set WAF mode (enforce or shadow). Accepts mode as query param or JSON body."""
    target_mode = mode
    if target_mode is None:
        try:
            body = await request.json()
            if isinstance(body, dict) and "mode" in body:
                target_mode = WAFModeEnum(body["mode"])
        except Exception:
            pass
    if target_mode is None:
        raise HTTPException(status_code=422, detail="Mode parameter required (query param ?mode= or JSON body {'mode': '...'})")
    engine = get_risk_engine()
    engine.update_policy(mode=target_mode)
    return {"mode": engine.mode.value, "message": f"WAF mode set to {target_mode.value}"}


@router.get("/policy", response_model=PolicyResponse)
async def get_policy():
    """Get current WAF policy."""
    engine = get_risk_engine()
    policy = engine.get_policy()
    return PolicyResponse(
        mode=engine.mode,
        thresholds=RiskThresholds(**policy["thresholds"]),
        weights=RiskWeights(**policy["weights"]),
        updated_at=__import__("datetime").datetime.utcnow(),
    )


@router.put("/policy", response_model=PolicyResponse)
async def update_policy(update: PolicyUpdateRequest):
    """Update WAF policy."""
    engine = get_risk_engine()
    engine.update_policy(
        thresholds=update.thresholds,
        weights=update.weights,
        mode=update.mode,
    )
    policy = engine.get_policy()
    return PolicyResponse(
        mode=engine.mode,
        thresholds=RiskThresholds(**policy["thresholds"]),
        weights=RiskWeights(**policy["weights"]),
        updated_at=__import__("datetime").datetime.utcnow(),
    )


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    feedback: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """Submit analyst feedback on a decision."""
    # Verify request exists
    result = await db.execute(
        select(RequestEvent).where(RequestEvent.request_id == feedback.request_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Request not found")

    # Create feedback
    fb = AnalystFeedback(
        request_id=feedback.request_id,
        analyst_label=feedback.analyst_label,
        previous_decision=event.decision,
        reason=feedback.reason,
    )
    db.add(fb)
    await db.commit()
    await db.refresh(fb)

    return FeedbackResponse(
        id=fb.id,
        request_id=fb.request_id,
        analyst_label=fb.analyst_label,
        previous_decision=fb.previous_decision,
        reason=fb.reason,
        created_at=fb.created_at,
    )


@router.get("/events", response_model=List[RequestEventResponse])
async def get_events(
    limit: int = 100,
    offset: int = 0,
    decision: Optional[DecisionEnum] = None,
    attack_type: Optional[ThreatTypeEnum] = None,
    source_ip: Optional[str] = None,
    session_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get recent request events with filters."""
    query = select(RequestEvent).order_by(desc(RequestEvent.timestamp))

    if decision:
        query = query.where(RequestEvent.decision == decision)
    if attack_type:
        query = query.where(RequestEvent.attack_type == attack_type)
    if source_ip:
        query = query.where(RequestEvent.source_ip == source_ip)
    if session_id:
        query = query.where(RequestEvent.session_id == session_id)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    events = result.scalars().all()

    return [RequestEventResponse.model_validate(e) for e in events]


@router.get("/events/{request_id}", response_model=RequestEventResponse)
async def get_event(
    request_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific request event."""
    result = await db.execute(
        select(RequestEvent).where(RequestEvent.request_id == request_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return RequestEventResponse.model_validate(event)


@router.get("/events/{request_id}/explanation")
async def get_event_explanation(
    request_id: str,
    waf: WAFGateway = Depends(get_waf_gateway),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed explanation for a request decision."""
    # Get event
    result = await db.execute(
        select(RequestEvent).where(RequestEvent.request_id == request_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Reconstruct explanation from stored data
    from app.risk.engine import RiskInput, RiskEngine
    from app.explainability.explainer import get_explainer

    risk_input = RiskInput(
        transformer_score=event.transformer_score or 0,
        anomaly_score=event.anomaly_score or 0,
        session_score=event.session_score or 0,
        application_score=event.application_score or 0,
        rule_score=event.rule_score or 0,
        endpoint_sensitivity="medium",  # Would need to look up
    )

    engine = get_risk_engine()
    risk_result = engine.calculate(risk_input)

    explainer = get_explainer()
    explanation = explainer.explain(
        request_id=request_id,
        risk_input=risk_input,
        risk_result=risk_result,
    )

    return explainer.to_dict(explanation)


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Get WAF statistics."""
    # Total requests
    total = await db.scalar(select(func.count(RequestEvent.id)))

    # By decision
    decisions = await db.execute(
        select(RequestEvent.decision, func.count(RequestEvent.id))
        .group_by(RequestEvent.decision)
    )
    decision_counts = {d.value: c for d, c in decisions.all()}

    # By attack type
    attacks = await db.execute(
        select(RequestEvent.attack_type, func.count(RequestEvent.id))
        .where(RequestEvent.attack_type.is_not(None))
        .group_by(RequestEvent.attack_type)
    )
    attack_counts = {a.value: c for a, c in attacks.all()}

    # Recent threats (last hour)
    from datetime import datetime, timedelta
    hour_ago = datetime.utcnow() - timedelta(hours=1)
    recent_threats = await db.scalar(
        select(func.count(RequestEvent.id))
        .where(RequestEvent.timestamp >= hour_ago)
        .where(RequestEvent.attack_type.is_not(None))
    )

    # Avg latency
    avg_latency = await db.scalar(
        select(func.avg(RequestEvent.latency_ms))
        .where(RequestEvent.latency_ms.is_not(None))
    )

    return {
        "total_requests": total or 0,
        "decisions": decision_counts,
        "attack_types": attack_counts,
        "recent_threats_1h": recent_threats or 0,
        "avg_latency_ms": round(avg_latency or 0, 1),
    }


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    from app.database import engine
    from app.ml.inference import get_inference_service
    import redis.asyncio as redis

    # Check database
    db_status = "healthy"
    try:
        async with engine.connect() as conn:
            await conn.execute(select(1))
    except Exception:
        db_status = "unhealthy"

    # Check Redis
    redis_status = "healthy"
    try:
        r = redis.from_url(__import__("app.config").config.get_settings().redis_url)
        await r.ping()
        await r.close()
    except Exception:
        redis_status = "unhealthy"

    # Check model
    ml_service = get_inference_service()
    model_status = "ready" if ml_service.is_loaded() else "not_loaded"

    return HealthResponse(
        api="healthy",
        database=db_status,
        redis=redis_status,
        model=model_status,
        version="0.1.0",
    )