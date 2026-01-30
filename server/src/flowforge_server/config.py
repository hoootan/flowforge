"""Server configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """FlowForge server settings."""

    model_config = SettingsConfigDict(
        env_prefix="FLOWFORGE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment
    env: Literal["development", "staging", "production"] = "development"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1

    # Database
    database_url: str = "postgresql+asyncpg://flowforge:flowforge@localhost:5432/flowforge"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Authentication
    api_key_header: str = "X-FlowForge-API-Key"
    signature_header: str = "X-FlowForge-Signature"

    # Execution
    default_retries: int = 3
    default_timeout_seconds: int = 300  # 5 minutes
    max_timeout_seconds: int = 3600  # 1 hour

    # Queue
    queue_prefix: str = "flowforge"
    max_concurrent_jobs: int = 100
    job_timeout_seconds: int = 600  # 10 minutes

    # Logging
    log_level: str = "INFO"
    log_format: Literal["json", "console"] = "console"

    # CORS (allow_credentials must be False when using wildcard "*")
    cors_origins: list[str] = ["*"]
    cors_allow_credentials: bool = False

    # AI Provider Configuration
    providers_config_path: str | None = None  # Path to YAML config file

    # Default AI settings
    default_ai_model: str = "claude-sonnet-4-5-20250514"
    default_fallback_chain: str = "default"  # default, fast, smart
    enable_provider_fallback: bool = True
    enable_provider_health_check: bool = True
    provider_health_check_interval: float = 60.0  # seconds

    # AI Provider API Keys (loaded from env)
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    google_api_key: str | None = None
    mistral_api_key: str | None = None
    cohere_api_key: str | None = None

    # AI Provider Timeouts
    ai_timeout_seconds: float = 60.0
    ai_connect_timeout_seconds: float = 10.0

    # JWT Authentication
    jwt_secret: str | None = None  # Required for JWT token support
    jwt_algorithm: str = "HS256"
    jwt_default_expiry_seconds: int = 3600  # 1 hour

    @property
    def is_development(self) -> bool:
        return self.env == "development"

    @property
    def jwt_enabled(self) -> bool:
        return self.jwt_secret is not None

    @property
    def is_production(self) -> bool:
        return self.env == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
