from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum


class DecisionEnum(str, Enum):
    ALLOW = "allow"
    MONITOR = "monitor"
    RATE_LIMIT = "rate_limit"
    CHALLENGE = "challenge"
    BLOCK = "block"
    WOULD_BLOCK = "would_block"


class ThreatTypeEnum(str, Enum):
    BENIGN = "benign"
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    PATH_TRAVERSAL = "path_traversal"
    COMMAND_INJECTION = "command_injection"
    OTHER_MALICIOUS = "other_malicious"


class SeverityEnum(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SensitivityEnum(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WAFModeEnum(str, Enum):
    ENFORCE = "enforce"
    SHADOW = "shadow"


# Request/Response schemas for WAF inspection
class WAFInspectRequest(BaseModel):
    method: str = Field(..., pattern="^(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)$")
    path: str = Field(..., max_length=2048)
    query: str = Field(default="", max_length=8192)
    headers: Dict[str, str] = Field(default_factory=dict)
    body: str = Field(default="", max_length=1024 * 1024)
    source_ip: str = Field(..., max_length=45)
    session_id: Optional[str] = Field(default=None, max_length=64)
    user_id: Optional[str] = Field(default=None, max_length=64)


class WAFInspectResponse(BaseModel):
    request_id: str
    decision: DecisionEnum
    risk_score: float = Field(..., ge=0.0, le=1.0)
    attack_type: Optional[ThreatTypeEnum] = None
    transformer_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    anomaly_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    session_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    application_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    rule_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    reasons: List[str] = Field(default_factory=list)
    signals: Dict[str, float] = Field(default_factory=dict)
    latency_ms: int
    timestamp: Optional[datetime] = None


# Event schemas
class RequestEventResponse(BaseModel):
    id: int
    request_id: str
    timestamp: datetime
    session_id: Optional[str]
    source_ip: str
    user_id: Optional[str]
    method: str
    path: str
    query_string: Optional[str]
    status_code: Optional[int]
    latency_ms: Optional[int]
    transformer_score: Optional[float]
    anomaly_score: Optional[float]
    session_score: Optional[float]
    application_score: Optional[float]
    rule_score: Optional[float]
    final_risk_score: float
    attack_type: Optional[ThreatTypeEnum]
    decision: DecisionEnum
    decision_reason: Optional[str]

    class Config:
        from_attributes = True


class SessionResponse(BaseModel):
    id: int
    session_key: str
    source_ip: str
    user_identifier: Optional[str]
    started_at: datetime
    last_seen_at: datetime
    request_count: int
    anomaly_score: float
    risk_score: float
    current_state: Optional[str]
    endpoint_count: int
    endpoint_sequence: Optional[List[Any]]
    risk_timeline: Optional[List[Dict[str, Any]]]

    class Config:
        from_attributes = True


class EndpointProfileResponse(BaseModel):
    id: int
    path_template: str
    method: str
    expected_parameters: Optional[Dict[str, Any]]
    authentication_required: bool
    sensitivity_level: SensitivityEnum
    allowed_content_types: Optional[List[str]]
    request_count: int
    baseline_stats: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True


class ThreatEventResponse(BaseModel):
    id: int
    request_id: str
    threat_type: ThreatTypeEnum
    severity: SeverityEnum
    confidence: float
    risk_score: float
    action: DecisionEnum
    explanation: Optional[str]
    signals: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


class AttackCampaignResponse(BaseModel):
    id: int
    session_id: Optional[str]
    source_ip: str
    first_seen: datetime
    last_seen: datetime
    threat_count: int
    campaign_score: float
    status: str
    threat_types: Optional[List[str]]
    endpoints_targeted: Optional[List[str]]

    class Config:
        from_attributes = True


# OpenAPI import
class OpenAPIImportRequest(BaseModel):
    spec: Dict[str, Any]
    source: Literal["json", "yaml", "url"] = "json"
    base_url: Optional[HttpUrl] = None


class OpenAPIImportResponse(BaseModel):
    imported: int
    updated: int
    errors: List[str]


# Policy schemas
class RiskThresholds(BaseModel):
    allow: float = Field(default=0.20, ge=0.0, le=1.0)
    monitor: float = Field(default=0.35, ge=0.0, le=1.0)
    rate_limit: float = Field(default=0.55, ge=0.0, le=1.0)
    challenge: float = Field(default=0.70, ge=0.0, le=1.0)
    block: float = Field(default=0.80, ge=0.0, le=1.0)


class RiskWeights(BaseModel):
    transformer: float = Field(default=0.35, ge=0.0, le=1.0)
    anomaly: float = Field(default=0.15, ge=0.0, le=1.0)
    session: float = Field(default=0.10, ge=0.0, le=1.0)
    application: float = Field(default=0.10, ge=0.0, le=1.0)
    rules: float = Field(default=0.30, ge=0.0, le=1.0)


class PolicyResponse(BaseModel):
    mode: WAFModeEnum
    thresholds: RiskThresholds
    weights: RiskWeights
    updated_at: datetime


class PolicyUpdateRequest(BaseModel):
    mode: Optional[WAFModeEnum] = None
    thresholds: Optional[RiskThresholds] = None
    weights: Optional[RiskWeights] = None


# Batch analysis
class BatchAnalyzeRequest(BaseModel):
    file_content: str
    filename: str
    content_type: Literal["csv", "json"]
    has_labels: bool = False


class BatchAnalyzeResponse(BaseModel):
    run_id: str
    status: str
    total_samples: int
    processed: int
    threats_detected: int
    blocked: int
    allowed: int
    precision: Optional[float]
    recall: Optional[float]
    f1: Optional[float]
    false_positive_rate: Optional[float]


class BatchRunResponse(BaseModel):
    id: str
    run_name: str
    dataset_name: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_samples: int
    results: Optional[List[Dict[str, Any]]] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1: Optional[float] = None
    false_positive_rate: Optional[float] = None


# Attack Lab
class AttackLabRunRequest(BaseModel):
    attack_family: Literal[
        "sql_injection",
        "xss",
        "path_traversal",
        "command_injection",
        "mixed"
    ] = "mixed"
    base_payloads: Optional[List[str]] = None
    variant_count: int = Field(default=25, ge=1, le=100)
    target_endpoint: str = "/search"


class AttackVariantResult(BaseModel):
    variant: str
    original: str
    transformations: List[str]
    detected: bool
    risk_score: float
    decision: DecisionEnum
    attack_type: Optional[ThreatTypeEnum]
    latency_ms: int


class AttackLabRunResponse(BaseModel):
    run_id: str
    attack_family: str
    total_variants: int
    detected: int
    missed: int
    detection_rate: float
    avg_latency_ms: float
    variants: List[AttackVariantResult]


# Model & Evaluation
class ModelInfo(BaseModel):
    id: int
    name: str
    version: str
    artifact_path: str
    training_dataset: Optional[str]
    precision: Optional[float]
    recall: Optional[float]
    f1: Optional[float]
    validation_date: Optional[datetime]
    active: bool
    notes: Optional[str]

    class Config:
        from_attributes = True


class EvaluationMetrics(BaseModel):
    accuracy: float
    precision: float
    recall: float
    f1: float
    false_positive_rate: float
    per_class: Dict[str, Dict[str, float]]
    confusion_matrix: List[List[int]]
    latency_ms: float
    throughput: float
    known_attack_detection_rate: Optional[float]
    unseen_variant_detection_rate: Optional[float]


class EvaluationRunResponse(BaseModel):
    id: int
    run_name: str
    dataset_name: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_samples: int
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1: Optional[float] = None
    false_positive_rate: Optional[float] = None
    latency_ms: Optional[float] = None
    metrics: Optional[EvaluationMetrics] = None

    class Config:
        from_attributes = True


# Feedback
class FeedbackRequest(BaseModel):
    request_id: str
    analyst_label: ThreatTypeEnum
    reason: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: int
    request_id: str
    analyst_label: ThreatTypeEnum
    previous_decision: DecisionEnum
    reason: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# Health check
class HealthResponse(BaseModel):
    api: str
    database: str
    redis: str
    model: str
    version: str