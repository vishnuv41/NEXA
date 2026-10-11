from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Float,
    Boolean,
    ForeignKey,
    Index,
    JSON,
    Enum as SQLEnum,
    BigInteger,
    desc,
)
from sqlalchemy.orm import relationship, declared_attr
from sqlalchemy.sql import func
from datetime import datetime
from enum import Enum as PyEnum
import uuid

from app.database import Base


class DecisionEnum(str, PyEnum):
    ALLOW = "allow"
    MONITOR = "monitor"
    RATE_LIMIT = "rate_limit"
    CHALLENGE = "challenge"
    BLOCK = "block"
    WOULD_BLOCK = "would_block"


class ThreatTypeEnum(str, PyEnum):
    BENIGN = "benign"
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    PATH_TRAVERSAL = "path_traversal"
    COMMAND_INJECTION = "command_injection"
    OTHER_MALICIOUS = "other_malicious"


class SeverityEnum(str, PyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SensitivityEnum(str, PyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RequestEvent(Base):
    __tablename__ = "request_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    request_id = Column(String(64), unique=True, nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=func.now(), index=True)

    session_id = Column(String(64), nullable=True, index=True)
    source_ip = Column(String(45), nullable=False, index=True)
    user_id = Column(String(64), nullable=True, index=True)

    method = Column(String(10), nullable=False)
    scheme = Column(String(10), nullable=False)
    host = Column(String(255), nullable=False)
    path = Column(String(2048), nullable=False)
    query_string = Column(Text, nullable=True)
    headers_summary = Column(JSON, nullable=True)
    body_summary = Column(Text, nullable=True)

    status_code = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)

    endpoint_id = Column(BigInteger, ForeignKey("endpoint_profiles.id"), nullable=True, index=True)

    transformer_score = Column(Float, nullable=True)
    anomaly_score = Column(Float, nullable=True)
    session_score = Column(Float, nullable=True)
    application_score = Column(Float, nullable=True)
    rule_score = Column(Float, nullable=True)
    final_risk_score = Column(Float, nullable=False, default=0.0, index=True)

    attack_type = Column(SQLEnum(ThreatTypeEnum), nullable=True, index=True)
    decision = Column(SQLEnum(DecisionEnum), nullable=False, default=DecisionEnum.ALLOW, index=True)
    decision_reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())

    endpoint = relationship("EndpointProfile", back_populates="requests")
    threat_events = relationship("ThreatEvent", back_populates="request", cascade="all, delete-orphan")
    analyst_feedback = relationship("AnalystFeedback", back_populates="request", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_request_events_timestamp_desc", desc("timestamp")),
        Index("ix_request_events_source_ip_timestamp", "source_ip", "timestamp"),
        Index("ix_request_events_decision_timestamp", "decision", "timestamp"),
    )


class Session(Base):
    __tablename__ = "sessions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_key = Column(String(64), unique=True, nullable=False, index=True)
    source_ip = Column(String(45), nullable=False, index=True)
    user_identifier = Column(String(128), nullable=True, index=True)

    started_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    last_seen_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now(), index=True)

    request_count = Column(Integer, nullable=False, default=0)
    anomaly_score = Column(Float, nullable=False, default=0.0)
    risk_score = Column(Float, nullable=False, default=0.0)
    current_state = Column(String(64), nullable=True)
    endpoint_count = Column(Integer, nullable=False, default=0)

    endpoint_sequence = Column(JSON, nullable=True)
    risk_timeline = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_sessions_source_ip_last_seen", "source_ip", "last_seen_at"),
        Index("ix_sessions_risk_score", "risk_score"),
    )


class EndpointProfile(Base):
    __tablename__ = "endpoint_profiles"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    path_template = Column(String(512), nullable=False, index=True)
    method = Column(String(10), nullable=False)

    expected_parameters = Column(JSON, nullable=True)
    authentication_required = Column(Boolean, nullable=False, default=False)
    sensitivity_level = Column(SQLEnum(SensitivityEnum), nullable=False, default=SensitivityEnum.LOW)
    allowed_content_types = Column(JSON, nullable=True)

    request_count = Column(Integer, nullable=False, default=0)
    baseline_stats = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())

    requests = relationship("RequestEvent", back_populates="endpoint")

    __table_args__ = (
        Index("ix_endpoint_profiles_path_method", "path_template", "method"),
    )


class ThreatEvent(Base):
    __tablename__ = "threat_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    request_id = Column(String(64), ForeignKey("request_events.request_id"), nullable=False, index=True)
    threat_type = Column(SQLEnum(ThreatTypeEnum), nullable=False, index=True)
    severity = Column(SQLEnum(SeverityEnum), nullable=False, default=SeverityEnum.MEDIUM)

    confidence = Column(Float, nullable=False)
    risk_score = Column(Float, nullable=False)
    action = Column(SQLEnum(DecisionEnum), nullable=False)

    explanation = Column(Text, nullable=True)
    signals = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), index=True)

    request = relationship("RequestEvent", back_populates="threat_events")

    __table_args__ = (
        Index("ix_threat_events_type_created", "threat_type", "created_at"),
        Index("ix_threat_events_severity", "severity"),
    )


class AttackCampaign(Base):
    __tablename__ = "attack_campaigns"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(String(64), nullable=True, index=True)
    source_ip = Column(String(45), nullable=False, index=True)

    first_seen = Column(DateTime(timezone=True), nullable=False, default=func.now())
    last_seen = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())

    threat_count = Column(Integer, nullable=False, default=0)
    campaign_score = Column(Float, nullable=False, default=0.0)
    status = Column(String(32), nullable=False, default="active")

    threat_types = Column(JSON, nullable=True)
    endpoints_targeted = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_attack_campaigns_source_ip_status", "source_ip", "status"),
    )


class AnalystFeedback(Base):
    __tablename__ = "analyst_feedback"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    request_id = Column(String(64), ForeignKey("request_events.request_id"), nullable=False, index=True)

    analyst_label = Column(SQLEnum(ThreatTypeEnum), nullable=False)
    previous_decision = Column(SQLEnum(DecisionEnum), nullable=False)
    reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), index=True)

    request = relationship("RequestEvent", back_populates="analyst_feedback")

    __table_args__ = (
        Index("ix_analyst_feedback_label", "analyst_label"),
    )


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    version = Column(String(32), nullable=False)
    artifact_path = Column(String(512), nullable=False)

    training_dataset = Column(String(256), nullable=True)
    precision = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)
    f1 = Column(Float, nullable=True)

    validation_date = Column(DateTime(timezone=True), nullable=True)
    active = Column(Boolean, nullable=False, default=False)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())

    __table_args__ = (
        Index("ix_model_versions_active", "active"),
    )


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    run_name = Column(String(128), nullable=False)
    dataset_name = Column(String(128), nullable=False)

    started_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    total_samples = Column(Integer, nullable=False, default=0)
    precision = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)
    f1 = Column(Float, nullable=True)
    false_positive_rate = Column(Float, nullable=True)

    latency_ms = Column(Float, nullable=True)
    throughput = Column(Float, nullable=True)

    known_attack_detection_rate = Column(Float, nullable=True)
    unseen_variant_detection_rate = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())

    __table_args__ = (
        Index("ix_evaluation_runs_dataset", "dataset_name"),
    )