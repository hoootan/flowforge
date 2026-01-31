"""Pydantic schemas for Usage API operations."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class UsageSummary(BaseModel):
    """Aggregate usage summary."""

    total_requests: int = Field(..., description="Total number of AI requests")
    total_tokens: int = Field(..., description="Total tokens used")
    prompt_tokens: int = Field(..., description="Total prompt/input tokens")
    completion_tokens: int = Field(..., description="Total completion/output tokens")
    total_cost_usd: float = Field(..., description="Total cost in USD")
    avg_latency_ms: float = Field(..., description="Average latency in milliseconds")
    period_start: datetime | None = Field(None, description="Start of the period")
    period_end: datetime | None = Field(None, description="End of the period")


class UsageByProvider(BaseModel):
    """Usage breakdown by provider."""

    provider: str = Field(..., description="Provider name")
    requests: int = Field(..., description="Number of requests")
    total_tokens: int = Field(..., description="Total tokens used")
    cost_usd: float = Field(..., description="Cost in USD")
    avg_latency_ms: float = Field(..., description="Average latency in ms")


class UsageByModel(BaseModel):
    """Usage breakdown by model."""

    model: str = Field(..., description="Model name")
    provider: str = Field(..., description="Provider name")
    requests: int = Field(..., description="Number of requests")
    total_tokens: int = Field(..., description="Total tokens used")
    cost_usd: float = Field(..., description="Cost in USD")
    avg_latency_ms: float = Field(..., description="Average latency in ms")


class DailyUsage(BaseModel):
    """Daily usage statistics."""

    date: str = Field(..., description="Date (YYYY-MM-DD)")
    requests: int = Field(..., description="Number of requests")
    total_tokens: int = Field(..., description="Total tokens used")
    cost_usd: float = Field(..., description="Cost in USD")


class UsageSummaryResponse(BaseModel):
    """Response for usage summary endpoint."""

    summary: UsageSummary


class UsageByProviderResponse(BaseModel):
    """Response for usage by provider endpoint."""

    providers: list[UsageByProvider]


class UsageByModelResponse(BaseModel):
    """Response for usage by model endpoint."""

    models: list[UsageByModel]


class DailyUsageResponse(BaseModel):
    """Response for daily usage endpoint."""

    daily: list[DailyUsage]


class RunUsageResponse(BaseModel):
    """Usage for a specific run."""

    run_id: str = Field(..., description="Run ID")
    total_requests: int = Field(..., description="Number of AI requests in this run")
    total_tokens: int = Field(..., description="Total tokens used")
    total_cost_usd: float = Field(..., description="Total cost in USD")
    by_step: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Usage breakdown by step",
    )
