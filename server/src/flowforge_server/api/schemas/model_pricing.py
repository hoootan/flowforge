"""Pydantic schemas for Model Pricing API operations."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# Source of pricing data
PricingSource = Literal["tenant", "global", "default", "fallback"]


class ModelPricingCreate(BaseModel):
    """Schema for creating a new model pricing config."""

    model_id: str = Field(
        ...,
        description="Model identifier (e.g., 'gpt-5.3', 'claude-sonnet-4-6')",
        min_length=1,
        max_length=255,
        examples=["gpt-5.3", "claude-sonnet-4-6"],
    )

    provider: str = Field(
        ...,
        description="Provider name (e.g., 'openai', 'anthropic', 'google')",
        min_length=1,
        max_length=64,
        examples=["openai", "anthropic", "google"],
    )

    input_price_per_m: float = Field(
        ...,
        description="Price per 1 million input tokens in USD",
        ge=0,
        examples=[2.50, 3.00, 0.15],
    )

    output_price_per_m: float = Field(
        ...,
        description="Price per 1 million output tokens in USD",
        ge=0,
        examples=[10.00, 15.00, 0.60],
    )

    display_name: str | None = Field(
        None,
        description="User-friendly display name for the model",
        max_length=255,
        examples=["GPT-4o", "Claude 3.5 Sonnet"],
    )

    is_global: bool = Field(
        default=False,
        description="If true, creates global pricing (applies to all tenants as default). Requires admin.",
    )


class ModelPricingUpdate(BaseModel):
    """Schema for updating a model pricing config."""

    input_price_per_m: float | None = Field(
        None,
        description="New price per 1 million input tokens in USD",
        ge=0,
    )

    output_price_per_m: float | None = Field(
        None,
        description="New price per 1 million output tokens in USD",
        ge=0,
    )

    display_name: str | None = Field(
        None,
        description="New display name",
        max_length=255,
    )

    is_active: bool | None = Field(
        None,
        description="Enable or disable this pricing config",
    )


class ModelPricingResponse(BaseModel):
    """Schema for model pricing response."""

    id: str = Field(..., description="Pricing config ID")
    model_id: str = Field(..., description="Model identifier")
    provider: str = Field(..., description="Provider name")
    input_price_per_m: float = Field(..., description="Price per 1M input tokens (USD)")
    output_price_per_m: float = Field(..., description="Price per 1M output tokens (USD)")
    display_name: str | None = Field(None, description="User-friendly display name")
    is_active: bool = Field(..., description="Whether this config is active")
    is_global: bool = Field(..., description="Whether this is global pricing (no tenant)")
    created_at: datetime = Field(..., description="Creation time")
    updated_at: datetime = Field(..., description="Last update time")

    model_config = {"from_attributes": True}


class ModelPricingListResponse(BaseModel):
    """Schema for listing model pricing configs."""

    pricing_configs: list[ModelPricingResponse]
    total: int


class EffectiveModelPricing(BaseModel):
    """
    Resolved pricing for a model with source indicator.

    This shows the effective pricing that will be used for cost calculations,
    along with where that pricing came from.
    """

    model_id: str = Field(..., description="Model identifier")
    provider: str = Field(..., description="Provider name")
    input_price_per_m: float = Field(..., description="Effective price per 1M input tokens (USD)")
    output_price_per_m: float = Field(..., description="Effective price per 1M output tokens (USD)")
    display_name: str | None = Field(None, description="Display name if available")
    source: PricingSource = Field(
        ...,
        description=(
            "Where this pricing came from: "
            "'tenant' = tenant-specific custom pricing, "
            "'global' = admin-set global defaults, "
            "'default' = hardcoded in DEFAULT_MODEL_CONFIGS, "
            "'fallback' = fallback pricing for unknown models"
        ),
    )
    pricing_id: str | None = Field(
        None,
        description="ID of the custom pricing config (if source is 'tenant' or 'global')",
    )


class EffectiveModelPricingListResponse(BaseModel):
    """Schema for listing all effective model pricing."""

    models: list[EffectiveModelPricing]
    total: int


class DefaultModelPricing(BaseModel):
    """Hardcoded default pricing from DEFAULT_MODEL_CONFIGS."""

    model_id: str = Field(..., description="Model identifier")
    provider: str = Field(..., description="Provider name")
    input_price_per_m: float = Field(..., description="Default price per 1M input tokens (USD)")
    output_price_per_m: float = Field(..., description="Default price per 1M output tokens (USD)")


class DefaultModelPricingListResponse(BaseModel):
    """Schema for listing hardcoded default pricing."""

    defaults: list[DefaultModelPricing]
    total: int
    fallback_input_price: float = Field(
        ...,
        description="Fallback price per 1M input tokens for unknown models (USD)",
    )
    fallback_output_price: float = Field(
        ...,
        description="Fallback price per 1M output tokens for unknown models (USD)",
    )
