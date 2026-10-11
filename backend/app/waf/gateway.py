from typing import Dict, Any, Optional
from dataclasses import dataclass
import time
import uuid
import logging
from datetime import datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.database import get_db_context
from app.models import RequestEvent, ThreatEvent, DecisionEnum, ThreatTypeEnum, SeverityEnum
from app.waf.normalizer import RequestNormalizer
from app.waf.rules import RuleEngine, get_rule_engine
from app.ml.inference import get_inference_service
from app.behavior.session import get_session_analyzer
from app.context.openapi import get_app_context
from app.risk.engine import get_risk_engine, RiskInput
from app.explainability.explainer import get_explainer, Explanation
from app.streaming.events import get_stream_manager
from app.schemas import WAFInspectRequest, WAFInspectResponse

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class WAFDecision:
    request_id: str
    decision: DecisionEnum
    risk_score: float
    attack_type: Optional[ThreatTypeEnum]
    transformer_score: Optional[float]
    anomaly_score: Optional[float]
    session_score: Optional[float]
    application_score: Optional[float]
    rule_score: Optional[float]
    reasons: list
    signals: Dict[str, float]
    latency_ms: int
    explanation: Optional[Explanation] = None


class WAFGateway:
    """Main WAF gateway that orchestrates all detection components."""

    def __init__(self):
        self.normalizer = RequestNormalizer()
        self.rule_engine = get_rule_engine()
        self.ml_service = get_inference_service()
        self.session_analyzer = get_session_analyzer()
        self.app_context = get_app_context()
        self.risk_engine = get_risk_engine()
        self.explainer = get_explainer()
        self.stream_manager = None

    async def initialize(self) -> None:
        """Initialize all components."""
        self.ml_service.load()
        self.stream_manager = await get_stream_manager()
        logger.info("WAF Gateway initialized")

    async def inspect(self, request: WAFInspectRequest) -> WAFDecision:
        """Inspect a request through the full WAF pipeline."""
        start_time = time.perf_counter()
        request_id = str(uuid.uuid4())[:16]

        # 1. Normalize request
        normalized = self.normalizer.normalize(request.model_dump())

        # 2. Run ML inference
        ml_result = self.ml_service.predict(normalized)

        # 3. Run rule engine
        rule_result = self.rule_engine.inspect_request(normalized)

        # 4. Check application context
        matched_endpoint = self.app_context.match_endpoint(request.method, request.path)
        app_result = self.app_context.analyze_request(normalized, matched_endpoint)

        # 5. Session analysis (preliminary risk for session)
        preliminary_risk = ml_result["malicious_probability"]
        session_result = await self.session_analyzer.analyze(
            normalized, preliminary_risk, "pending"
        )

        # 6. Calculate risk
        risk_input = RiskInput(
            transformer_score=ml_result["malicious_probability"],
            anomaly_score=ml_result["anomaly_score"],
            session_score=session_result["session_score"],
            application_score=app_result["score"],
            rule_score=rule_result["score"],
            endpoint_sensitivity=matched_endpoint.sensitivity.value if matched_endpoint else "low",
            ml_attack_class=ml_result.get("attack_class"),
            rule_categories=rule_result.get("categories"),
        )
        risk_result = self.risk_engine.calculate(risk_input)

        # 7. Generate explanation
        explanation = self.explainer.explain(
            request_id=request_id,
            risk_input=risk_input,
            risk_result=risk_result,
            ml_details=ml_result,
            rule_details=rule_result,
            session_details=session_result,
            app_details=app_result,
        )

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # 8. Create decision
        decision = WAFDecision(
            request_id=request_id,
            decision=risk_result.decision,
            risk_score=risk_result.final_risk_score,
            attack_type=risk_result.attack_type,
            transformer_score=ml_result["malicious_probability"],
            anomaly_score=ml_result["anomaly_score"],
            session_score=session_result["session_score"],
            application_score=app_result["score"],
            rule_score=rule_result["score"],
            reasons=risk_result.reasons,
            signals=risk_result.signal_breakdown,
            latency_ms=latency_ms,
            explanation=explanation,
        )

        # 9. Persist event
        await self._persist_event(request, normalized, decision, matched_endpoint)

        # 10. Update session with final decision
        await self.session_analyzer.analyze(normalized, risk_result.final_risk_score, risk_result.decision.value)

        # 11. Stream event
        await self._stream_event(decision, request, normalized, matched_endpoint)

        return decision

    async def _persist_event(
        self,
        request: WAFInspectRequest,
        normalized: Dict[str, Any],
        decision: WAFDecision,
        matched_endpoint,
    ) -> None:
        """Persist request event to database."""
        try:
            async with get_db_context() as db:
                # Create request event
                summary = self.normalizer.create_summary(normalized)

                event = RequestEvent(
                    request_id=decision.request_id,
                    session_id=decision.explanation.request_id if decision.explanation else None,
                    source_ip=request.source_ip,
                    user_id=request.user_id,
                    method=request.method,
                    scheme="http",
                    host=request.headers.get("host", "localhost"),
                    path=request.path,
                    query_string=request.query,
                    headers_summary=summary.get("headers_summary"),
                    body_summary=summary.get("body_summary"),
                    status_code=None,  # Will be set after proxy
                    latency_ms=decision.latency_ms,
                    endpoint_id=matched_endpoint.id if matched_endpoint else None,
                    transformer_score=decision.transformer_score,
                    anomaly_score=decision.anomaly_score,
                    session_score=decision.session_score,
                    application_score=decision.application_score,
                    rule_score=decision.rule_score,
                    final_risk_score=decision.risk_score,
                    attack_type=decision.attack_type,
                    decision=decision.decision,
                    decision_reason="; ".join(decision.reasons) if decision.reasons else None,
                )
                db.add(event)

                # Create threat event if malicious
                if decision.attack_type and decision.attack_type != ThreatTypeEnum.BENIGN:
                    severity = self._score_to_severity(decision.risk_score)
                    threat = ThreatEvent(
                        request_id=decision.request_id,
                        threat_type=decision.attack_type,
                        severity=severity,
                        confidence=decision.transformer_score or 0.0,
                        risk_score=decision.risk_score,
                        action=decision.decision,
                        explanation=decision.explanation.summary if decision.explanation else None,
                        signals=decision.signals,
                    )
                    db.add(threat)

                await db.commit()
        except Exception as e:
            logger.error(f"Failed to persist event: {e}")

    async def _stream_event(
        self,
        decision: WAFDecision,
        request: WAFInspectRequest,
        normalized: Dict[str, Any],
        matched_endpoint,
    ) -> None:
        """Stream event to Redis for real-time dashboard."""
        if not self.stream_manager or not self.stream_manager.is_connected():
            return

        event_data = {
            "type": "request",
            "request_id": decision.request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "method": request.method,
            "path": request.path,
            "query": request.query[:200] if request.query else "",
            "source_ip": request.source_ip,
            "session_id": request.session_id,
            "risk_score": decision.risk_score,
            "attack_type": decision.attack_type.value if decision.attack_type else None,
            "decision": decision.decision.value,
            "latency_ms": decision.latency_ms,
            "signals": decision.signals,
            "endpoint": {
                "path": matched_endpoint.path_template if matched_endpoint else request.path,
                "method": matched_endpoint.method if matched_endpoint else request.method,
                "sensitivity": matched_endpoint.sensitivity.value if matched_endpoint else "unknown",
            } if matched_endpoint else None,
        }

        await self.stream_manager.publish_event(event_data)

    def _score_to_severity(self, score: float) -> SeverityEnum:
        """Convert risk score to severity."""
        if score >= 0.8:
            return SeverityEnum.CRITICAL
        elif score >= 0.6:
            return SeverityEnum.HIGH
        elif score >= 0.4:
            return SeverityEnum.MEDIUM
        else:
            return SeverityEnum.LOW

    async def proxy_request(self, request: WAFInspectRequest) -> httpx.Response:
        """Proxy request to demo application."""
        url = f"{settings.demo_app_url}{request.path}"
        if request.query:
            url += f"?{request.query}"

        headers = dict(request.headers)
        headers.pop("host", None)
        headers.pop("content-length", None)

        async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
            response = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                content=request.body.encode() if request.body else None,
            )
        return response


# Singleton
_waf_gateway: Optional[WAFGateway] = None


async def get_waf_gateway() -> WAFGateway:
    global _waf_gateway
    if _waf_gateway is None:
        _waf_gateway = WAFGateway()
        await _waf_gateway.initialize()
    return _waf_gateway