from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging

from app.config import get_settings
from app.schemas import DecisionEnum, ThreatTypeEnum, RiskThresholds, RiskWeights, WAFModeEnum

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class RiskInput:
    """Input signals for risk calculation."""
    transformer_score: float = 0.0      # ML classifier malicious probability
    anomaly_score: float = 0.0          # Model uncertainty/anomaly
    session_score: float = 0.0          # Behavioral anomaly
    application_score: float = 0.0      # Contract violation
    rule_score: float = 0.0             # Deterministic rule matches
    endpoint_sensitivity: str = "low"   # low, medium, high, critical
    ml_attack_class: Optional[str] = None
    rule_categories: Optional[Dict[str, float]] = None


@dataclass
class RiskResult:
    """Risk calculation result."""
    final_risk_score: float
    decision: DecisionEnum
    attack_type: Optional[ThreatTypeEnum]
    reasons: List[str]
    signal_breakdown: Dict[str, float]
    threshold_used: str


class RiskEngine:
    """Calculates final risk score and makes enforcement decisions."""

    def __init__(self):
        self.thresholds = RiskThresholds()
        self.weights = RiskWeights()
        self.mode = WAFModeEnum.ENFORCE

    def update_policy(
        self,
        thresholds: Optional[RiskThresholds] = None,
        weights: Optional[RiskWeights] = None,
        mode: Optional[WAFModeEnum] = None,
    ) -> None:
        """Update risk policy configuration."""
        if thresholds:
            self.thresholds = thresholds
        if weights:
            # Validate weights sum to ~1.0
            total = (weights.transformer + weights.anomaly + weights.session +
                    weights.application + weights.rules)
            if abs(total - 1.0) > 0.01:
                logger.warning(f"Weights sum to {total}, normalizing")
                weights.transformer /= total
                weights.anomaly /= total
                weights.session /= total
                weights.application /= total
                weights.rules /= total
            self.weights = weights
        if mode:
            self.mode = mode

    def get_policy(self) -> Dict[str, Any]:
        """Get current policy."""
        return {
            "mode": self.mode.value,
            "thresholds": {
                "allow": self.thresholds.allow,
                "monitor": self.thresholds.monitor,
                "rate_limit": self.thresholds.rate_limit,
                "challenge": self.thresholds.challenge,
                "block": self.thresholds.block,
            },
            "weights": {
                "transformer": self.weights.transformer,
                "anomaly": self.weights.anomaly,
                "session": self.weights.session,
                "application": self.weights.application,
                "rules": self.weights.rules,
            },
        }

    def calculate(self, risk_input: RiskInput) -> RiskResult:
        """Calculate final risk score and decision."""
        # Normalize all inputs to [0, 1]
        signals = {
            "transformer": max(0.0, min(1.0, risk_input.transformer_score)),
            "anomaly": max(0.0, min(1.0, risk_input.anomaly_score)),
            "session": max(0.0, min(1.0, risk_input.session_score)),
            "application": max(0.0, min(1.0, risk_input.application_score)),
            "rules": max(0.0, min(1.0, risk_input.rule_score)),
        }

        # Weighted combination across all 5 dimensions
        weighted_score = (
            signals["transformer"] * self.weights.transformer +
            signals["anomaly"] * self.weights.anomaly +
            signals["session"] * self.weights.session +
            signals["application"] * self.weights.application +
            signals["rules"] * self.weights.rules
        )

        # High-confidence attack signal floor:
        # A direct signature match (e.g. SQLi / XSS payload) or strong ML classification
        # must not be washed out by an empty session or missing schema context.
        signal_floor = max(signals["rules"] * 0.95, signals["transformer"] * 0.90)
        base_score = max(weighted_score, signal_floor)

        # Sensitivity adjustment
        sensitivity_multiplier = {
            "low": 1.0,
            "medium": 1.1,
            "high": 1.2,
            "critical": 1.3,
        }.get(risk_input.endpoint_sensitivity.lower(), 1.0)

        final_score = min(1.0, base_score * sensitivity_multiplier)

        # Determine decision based on thresholds
        decision, threshold_name = self._evaluate_thresholds(final_score)

        # Determine attack type from signals
        attack_type = self._determine_attack_type(risk_input, signals)

        # Generate reasons
        reasons = self._generate_reasons(signals, risk_input, final_score)

        return RiskResult(
            final_risk_score=round(final_score, 3),
            decision=decision,
            attack_type=attack_type,
            reasons=reasons,
            signal_breakdown=signals,
            threshold_used=threshold_name,
        )

    def _evaluate_thresholds(self, score: float) -> tuple[DecisionEnum, str]:
        """Evaluate score against thresholds."""
        if self.mode == WAFModeEnum.SHADOW:
            # In shadow mode, return "would" decisions
            if score >= self.thresholds.block:
                return DecisionEnum.WOULD_BLOCK, "block"
            elif score >= self.thresholds.challenge:
                return DecisionEnum.WOULD_BLOCK, "challenge"  # Would challenge
            elif score >= self.thresholds.rate_limit:
                return DecisionEnum.MONITOR, "rate_limit"  # Would rate limit
            elif score >= self.thresholds.monitor:
                return DecisionEnum.MONITOR, "monitor"
            else:
                return DecisionEnum.ALLOW, "allow"

        # Enforcement mode
        if score >= self.thresholds.block:
            return DecisionEnum.BLOCK, "block"
        elif score >= self.thresholds.challenge:
            return DecisionEnum.CHALLENGE, "challenge"
        elif score >= self.thresholds.rate_limit:
            return DecisionEnum.RATE_LIMIT, "rate_limit"
        elif score >= self.thresholds.monitor:
            return DecisionEnum.MONITOR, "monitor"
        else:
            return DecisionEnum.ALLOW, "allow"

    def _determine_attack_type(
        self,
        risk_input: RiskInput,
        signals: Dict[str, float],
    ) -> Optional[ThreatTypeEnum]:
        """Determine primary attack type from signals."""
        category_map = {
            "sql_injection": ThreatTypeEnum.SQL_INJECTION,
            "xss": ThreatTypeEnum.XSS,
            "path_traversal": ThreatTypeEnum.PATH_TRAVERSAL,
            "command_injection": ThreatTypeEnum.COMMAND_INJECTION,
        }

        # 1. Match from rule engine categories (most specific)
        if risk_input.rule_categories and signals["rules"] > 0.3:
            sorted_cats = sorted(risk_input.rule_categories.items(), key=lambda x: x[1], reverse=True)
            for cat_name, cat_score in sorted_cats:
                if cat_score > 0.3:
                    if cat_name in category_map:
                        return category_map[cat_name]
                    return ThreatTypeEnum.OTHER_MALICIOUS

        # 2. Match from ML transformer classification
        if risk_input.ml_attack_class and risk_input.ml_attack_class != "benign":
            if risk_input.ml_attack_class in category_map:
                return category_map[risk_input.ml_attack_class]
            elif signals["transformer"] > 0.4:
                return ThreatTypeEnum.OTHER_MALICIOUS

        # 3. Fallback for elevated anomaly/malicious signals
        if signals["rules"] > 0.4 or signals["transformer"] > 0.5:
            return ThreatTypeEnum.OTHER_MALICIOUS

        return None

    def _generate_reasons(
        self,
        signals: Dict[str, float],
        risk_input: RiskInput,
        final_score: float,
    ) -> List[str]:
        """Generate human-readable reasons for the decision."""
        reasons = []

        # Signal-specific reasons
        if signals["transformer"] > 0.7:
            reasons.append("ML model detected malicious pattern")
        elif signals["transformer"] > 0.4:
            reasons.append("ML model shows elevated malicious probability")

        if signals["anomaly"] > 0.7:
            reasons.append("Request structure highly anomalous")
        elif signals["anomaly"] > 0.4:
            reasons.append("Request deviates from normal patterns")

        if signals["session"] > 0.7:
            reasons.append("Session behavior indicates automated/enumeration attack")
        elif signals["session"] > 0.4:
            reasons.append("Session shows unusual access patterns")

        if signals["application"] > 0.6:
            reasons.append("Request violates API contract")
        elif signals["application"] > 0.3:
            reasons.append("Request parameters deviate from endpoint specification")

        if signals["rules"] > 0.5:
            reasons.append("Deterministic rules matched known attack signatures")
        elif signals["rules"] > 0.2:
            reasons.append("Suspicious patterns detected by rule engine")

        # Sensitivity
        if risk_input.endpoint_sensitivity in ["high", "critical"]:
            reasons.append(f"High-sensitivity endpoint ({risk_input.endpoint_sensitivity})")

        # Final score context
        if final_score > 0.8:
            reasons.append("Critical risk level - immediate action warranted")
        elif final_score > 0.6:
            reasons.append("High risk level - strong indicators of attack")
        elif final_score > 0.4:
            reasons.append("Moderate risk level - suspicious characteristics")

        return reasons


# Singleton
_risk_engine: Optional[RiskEngine] = None


def get_risk_engine() -> RiskEngine:
    global _risk_engine
    if _risk_engine is None:
        _risk_engine = RiskEngine()
        # Load from settings
        _risk_engine.update_policy(
            thresholds=RiskThresholds(
                allow=settings.risk_allow_threshold,
                monitor=settings.risk_monitor_threshold,
                rate_limit=settings.risk_rate_limit_threshold,
                challenge=settings.risk_challenge_threshold,
                block=settings.risk_block_threshold,
            ),
            weights=RiskWeights(
                transformer=settings.weight_transformer,
                anomaly=settings.weight_anomaly,
                session=settings.weight_session,
                application=settings.weight_application,
                rules=settings.weight_rules,
            ),
            mode=WAFModeEnum(settings.waf_mode),
        )
    return _risk_engine