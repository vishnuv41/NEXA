from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        protected_namespaces=(),
    )

    # Application
    app_name: str = "NEXA WAF"
    app_version: str = "0.1.0"
    debug: bool = True
    environment: str = "development"

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://waf:waf@localhost:5432/waf",
        description="PostgreSQL async connection URL"
    )
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    redis_max_connections: int = 20

    # WAF
    waf_mode: str = Field(
        default="enforce",
        description="WAF mode: enforce or shadow"
    )
    demo_app_url: str = Field(
        default="http://localhost:8001",
        description="Demo application base URL"
    )
    request_timeout: float = 30.0
    max_body_size: int = 10 * 1024 * 1024  # 10MB

    # Risk Thresholds
    risk_allow_threshold: float = 0.20
    risk_monitor_threshold: float = 0.35
    risk_rate_limit_threshold: float = 0.55
    risk_challenge_threshold: float = 0.70
    risk_block_threshold: float = 0.80

    # Risk Weights (must sum to 1.0)
    weight_transformer: float = 0.35
    weight_anomaly: float = 0.15
    weight_session: float = 0.10
    weight_application: float = 0.10
    weight_rules: float = 0.30

    # ML Model
    model_path: str = Field(
        default="./ml/artifacts/model.pt",
        description="Path to trained model artifact"
    )
    tokenizer_path: str = Field(
        default="./ml/artifacts/tokenizer",
        description="Path to tokenizer"
    )
    model_device: str = Field(
        default="cpu",
        description="Device for inference: cpu or cuda"
    )
    max_sequence_length: int = 512
    inference_batch_size: int = 32

    # Session
    session_ttl_seconds: int = 3600
    session_max_requests: int = 1000
    session_cleanup_interval: int = 300

    # Rate Limiting
    rate_limit_default: int = 100
    rate_limit_window_seconds: int = 60
    rate_limit_storage: str = "redis"

    # Streaming
    stream_key: str = "waf:events"
    stream_max_len: int = 10000
    sse_heartbeat_interval: int = 15

    # Batch
    batch_max_file_size: int = 100 * 1024 * 1024  # 100MB
    batch_max_rows: int = 100000
    batch_worker_concurrency: int = 4

    # Attack Lab
    attack_lab_max_variants: int = 100
    attack_lab_timeout_seconds: int = 300

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Security
    secret_key: str = Field(
        default="dev-secret-change-in-production",
        description="Secret key for signing"
    )
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8001"],
        description="Allowed CORS origins"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()