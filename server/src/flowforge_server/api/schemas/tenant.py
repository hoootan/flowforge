"""Pydantic schemas for tenant/workspace settings."""

from pydantic import BaseModel, Field


class ConcurrencySettings(BaseModel):
    """Workspace-level concurrency and step-execution defaults."""

    max_concurrent_runs: int = Field(
        default=500,
        ge=1,
        le=100_000,
        description="Maximum runs that may be in 'running' state simultaneously across all functions in this workspace.",
    )
    per_function_default: int = Field(
        default=50,
        ge=1,
        le=10_000,
        description="Per-function concurrency cap used when a Function does not declare its own.",
    )
    default_step_timeout_s: int = Field(
        default=60,
        ge=1,
        le=3600,
        description="Default soft timeout for individual steps, in seconds.",
    )
    use_event_id_idempotency: bool = Field(
        default=True,
        description="When true, the trigger event id becomes the new Run's idempotency key, preventing duplicate runs from a redelivered event.",
    )


class ConcurrencySettingsUpdate(BaseModel):
    """Partial update for concurrency settings."""

    max_concurrent_runs: int | None = Field(default=None, ge=1, le=100_000)
    per_function_default: int | None = Field(default=None, ge=1, le=10_000)
    default_step_timeout_s: int | None = Field(default=None, ge=1, le=3600)
    use_event_id_idempotency: bool | None = None


# Default constants exposed for non-API call-sites that need the same defaults
DEFAULT_CONCURRENCY = ConcurrencySettings()
