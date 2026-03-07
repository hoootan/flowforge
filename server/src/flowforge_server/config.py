"""Server configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env into os.environ so non-FLOWFORGE_ vars (e.g. TAVILY_API_KEY,
# GOOGLE_API_KEY) are available to builtin tool implementations.
load_dotenv()


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

    # CORS Configuration
    # In production, set FLOWFORGE_CORS_ALLOWED_ORIGINS to comma-separated list
    # Example: FLOWFORGE_CORS_ALLOWED_ORIGINS=https://app.example.com,https://dashboard.example.com
    cors_allowed_origins: str = ""  # Comma-separated list for production
    cors_allow_credentials: bool = True  # Allow credentials when origins are specified

    @property
    def cors_origins(self) -> list[str]:
        """
        Get CORS origins based on environment.

        In development: Allow all origins (wildcard)
        In production: Use explicitly configured origins only
        """
        if self.is_development:
            return ["*"]

        if self.cors_allowed_origins:
            return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

        # Production with no configured origins = no CORS (most secure default)
        return []

    @property
    def effective_cors_allow_credentials(self) -> bool:
        """Credentials must be False when using wildcard origins."""
        if "*" in self.cors_origins:
            return False
        return self.cors_allow_credentials

    # AI Provider Configuration
    providers_config_path: str | None = None  # Path to YAML config file

    # Default AI settings
    default_ai_model: str = "claude-sonnet-4-6"
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
    jwt_refresh_expiry_seconds: int = 86400  # 24 hours (reduced from 7 days for security)

    # Encryption (for storing sensitive data like AI provider API keys)
    encryption_key: str | None = None  # Required for secure credential storage
    encryption_salt: str | None = None  # Unique salt per installation for key derivation

    # Rate limiting and brute force protection
    login_rate_limit: int = 10  # Requests per minute per IP
    login_lockout_threshold: int = 5  # Failed attempts before lockout
    login_lockout_duration: int = 900  # Lockout duration in seconds (15 min)

    # OpenTelemetry / Observability
    otlp_endpoint: str | None = None  # OTLP collector endpoint (e.g., "http://localhost:4317")
    otlp_insecure: bool = True  # Use insecure connection for local development
    service_name: str = "flowforge-server"  # Service name for traces

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
