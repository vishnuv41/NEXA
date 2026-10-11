from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json
import logging

from app.schemas import DecisionEnum, ThreatTypeEnum
from app.risk.engine import RiskInput, RiskResult

logger = logging.getLogger(__name__)


@dataclass
class EvidenceItem:
    """Single piece of evidence for a decision."""
    id: str
    category: str  # transformer, anomaly, session, application, rules
    title: str
    description: str
    severity: str  # low, medium, high, critical
    score: float
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class Explanation:
    """Complete explanation for a WAF decision."""
    request_id: str
    decision: DecisionEnum
    risk_score: float
    attack_type: Optional[ThreatTypeEnum]
    summary: str
    evidence: List[EvidenceItem]
    signal_breakdown: Dict[str, float]
    policy_thresholds: Dict[str, float]


class DecisionExplainer:
    """Generates structured explanations for WAF decisions."""

    def __init__(self):
        self.evidence_templates = {
            "transformer": {
                "high": {
                    "title": "ML Model: Strong Malicious Classification",
                    "description": "The transformer model classified this request as malicious with high confidence.",
                },
                "medium": {
                    "title": "ML Model: Elevated Malicious Probability",
                    "description": "The transformer model shows elevated probability for malicious classes.",
                },
            },
            "anomaly": {
                "high": {
                    "title": "High Structural Anomaly",
                    "description": "The request structure deviates significantly from normal traffic patterns.",
                },
                "medium": {
                    "title": "Moderate Structural Anomaly",
                    "description": "The request shows unusual characteristics compared to baseline.",
                },
            },
            "session": {
                "high": {
                    "title": "Session Behavior: Automated Attack Pattern",
                    "description": "The session exhibits behavior consistent with automated enumeration or credential stuffing.",
                },
                "medium": {
                    "title": "Session Behavior: Unusual Access Pattern",
                    "description": "The session shows access patterns that deviate from normal user behavior.",
                },
            },
            "application": {
                "high": {
                    "title": "API Contract Violation",
                    "description": "The request violates the application's OpenAPI specification (type mismatch, missing params, etc.).",
                },
                "medium": {
                    "title": "Parameter Deviation from Contract",
                    "description": "Request parameters deviate from the expected endpoint contract.",
                },
            },
            "rules": {
                "high": {
                    "title": "Known Attack Signature Matched",
                    "description": "Deterministic rules detected known attack patterns (SQLi, XSS, traversal, etc.).",
                },
                "medium": {
                    "title": "Suspicious Pattern Detected",
                    "description": "Rule engine flagged suspicious but not definitively malicious patterns.",
                },
            },
        }

    def explain(
        self,
        request_id: str,
        risk_input: RiskInput,
        risk_result: RiskResult,
        ml_details: Optional[Dict[str, Any]] = None,
        rule_details: Optional[Dict[str, Any]] = None,
        session_details: Optional[Dict[str, Any]] = None,
        app_details: Optional[Dict[str, Any]] = None,
    ) -> Explanation:
        """Generate full explanation."""
        evidence = []

        # Transformer evidence
        if risk_input.transformer_score > 0.3:
            level = "high" if risk_input.transformer_score > 0.7 else "medium"
            template = self.evidence_templates["transformer"][level]
            evidence.append(EvidenceItem(
                id="ev_transformer",
                category="transformer",
                title=template["title"],
                description=template["description"],
                severity="critical" if level == "high" else "high",
                score=risk_input.transformer_score,
                raw_data={
                    "malicious_probability": risk_input.transformer_score,
                    "attack_class": ml_details.get("attack_class") if ml_details else None,
                    "attack_probabilities": ml_details.get("attack_probabilities") if ml_details else None,
                } if ml_details else None,
            ))

        # Anomaly evidence
        if risk_input.anomaly_score > 0.3:
            level = "high" if risk_input.anomaly_score > 0.7 else "medium"
            template = self.evidence_templates["anomaly"][level]
            evidence.append(EvidenceItem(
                id="ev_anomaly",
                category="anomaly",
                title=template["title"],
                description=template["description"],
                severity="high" if level == "high" else "medium",
                score=risk_input.anomaly_score,
                raw_data={"anomaly_score": risk_input.anomaly_score},
            ))

        # Session evidence
        if risk_input.session_score > 0.3:
            level = "high" if risk_input.session_score > 0.7 else "medium"
            template = self.evidence_templates["session"][level]
            session_reasons = session_details.get("reasons", []) if session_details else []
            evidence.append(EvidenceItem(
                id="ev_session",
                category="session",
                title=template["title"],
                description=template["description"] + (" " + "; ".join(session_reasons) if session_reasons else ""),
                severity="high" if level == "high" else "medium",
                score=risk_input.session_score,
                raw_data=session_details,
            ))

        # Application evidence
        if risk_input.application_score > 0.2:
            level = "high" if risk_input.application_score > 0.6 else "medium"
            template = self.evidence_templates["application"][level]
            app_reasons = app_details.get("reasons", []) if app_details else []
            evidence.append(EvidenceItem(
                id="ev_application",
                category="application",
                title=template["title"],
                description=template["description"] + (" " + "; ".join(app_reasons) if app_reasons else ""),
                severity="high" if level == "high" else "medium",
                score=risk_input.application_score,
                raw_data=app_details,
            ))

        # Rules evidence
        if risk_input.rule_score > 0.2:
            level = "high" if risk_input.rule_score > 0.5 else "medium"
            template = self.evidence_templates["rules"][level]
            matched_rules = rule_details.get("matches", []) if rule_details else []
            categories = rule_details.get("categories", {}) if rule_details else {}
            evidence.append(EvidenceItem(
                id="ev_rules",
                category="rules",
                title=template["title"],
                description=template["description"] + (f" Matched: {', '.join(categories.keys())}" if categories else ""),
                severity="critical" if level == "high" else "high",
                score=risk_input.rule_score,
                raw_data={
                    "matched_rules": matched_rules[:10],
                    "categories": categories,
                } if rule_details else None,
            ))

        # Sort evidence by severity and score
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        evidence.sort(key=lambda e: (severity_order.get(e.severity, 4), -e.score))

        # Generate summary
        summary = self._generate_summary(risk_result, evidence)

        return Explanation(
            request_id=request_id,
            decision=risk_result.decision,
            risk_score=risk_result.final_risk_score,
            attack_type=risk_result.attack_type,
            summary=summary,
            evidence=evidence,
            signal_breakdown=risk_result.signal_breakdown,
            policy_thresholds={
                "allow": 0.20,
                "monitor": 0.45,
                "rate_limit": 0.65,
                "challenge": 0.85,
                "block": 1.0,
            },
        )

    def _generate_summary(
        self,
        risk_result: RiskResult,
        evidence: List[EvidenceItem],
    ) -> str:
        """Generate human-readable summary."""
        decision = risk_result.decision.value.upper()
        score = risk_result.final_risk_score

        if risk_result.attack_type and risk_result.attack_type != ThreatTypeEnum.BENIGN:
            attack_str = f" ({risk_result.attack_type.value.replace('_', ' ').title()})"
        else:
            attack_str = ""

        if decision == "BLOCK":
            return f"Request blocked due to critical risk (score: {score:.0%}){attack_str}. {len(evidence)} evidence factors."
        elif decision == "CHALLENGE":
            return f"Challenge required due to high risk (score: {score:.0%}){attack_str}."
        elif decision == "RATE_LIMIT":
            return f"Rate limited due to elevated risk (score: {score:.0%}){attack_str}."
        elif decision == "MONITOR":
            return f"Request allowed but flagged for monitoring (score: {score:.0%}){attack_str}."
        elif decision == "WOULD_BLOCK":
            return f"[SHADOW MODE] Would block: critical risk (score: {score:.0%}){attack_str}."
        else:
            return f"Request allowed - low risk (score: {score:.0%})."

    def to_dict(self, explanation: Explanation) -> Dict[str, Any]:
        """Convert explanation to dictionary for API response."""
        return {
            "request_id": explanation.request_id,
            "decision": explanation.decision.value,
            "risk_score": explanation.risk_score,
            "attack_type": explanation.attack_type.value if explanation.attack_type else None,
            "summary": explanation.summary,
            "evidence": [
                {
                    "id": e.id,
                    "category": e.category,
                    "title": e.title,
                    "description": e.description,
                    "severity": e.severity,
                    "score": e.score,
                    "raw_data": e.raw_data,
                }
                for e in explanation.evidence
            ],
            "signal_breakdown": explanation.signal_breakdown,
            "policy_thresholds": explanation.policy_thresholds,
        }


# Singleton
_explainer: Optional[DecisionExplainer] = None


def get_explainer() -> DecisionExplainer:
    global _explainer
    if _explainer is None:
        _explainer = DecisionExplainer()
    return _explainer