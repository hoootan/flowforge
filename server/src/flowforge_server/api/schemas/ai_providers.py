"""Pydantic schemas for AI Provider API operations."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

# Known provider names
ProviderName = Literal["openai", "anthropic", "google", "mistral", "cohere", "custom"]


# Authentication type
AuthType = Literal["api_key", "oauth_token"]


class AIProviderCreate(BaseModel):
    """Schema for creating a new AI provider."""

    provider_name: ProviderName = Field(
        ...,
        description="Provider identifier",
        examples=["openai", "anthropic"],
    )

    api_key: str = Field(
        ...,
        description="The API key or OAuth token (will be encrypted)",
        min_length=1,
        max_length=500,
        examples=["sk-..."],
    )

    auth_type: AuthType = Field(
        default="api_key",
        description="Authentication type: 'api_key' for standard API keys, 'oauth_token' for OAuth bearer tokens",
    )

    display_name: str | None = Field(
        None,
        description="User-friendly name (defaults to provider's standard name)",
        max_length=255,
        examples=["Production OpenAI"],
    )

    base_url: str | None = Field(
        None,
        description="Custom API endpoint (for self-hosted or proxied providers)",
        examples=["https://api.custom-provider.com/v1"],
    )

    is_default: bool = Field(
        default=False,
        description="Whether this should be the default provider for the tenant",
    )

    config: dict[str, Any] | None = Field(
        None,
        description="Additional configuration (model preferences, rate limits, etc.)",
    )


class AIProviderUpdate(BaseModel):
    """Schema for updating an AI provider."""

    api_key: str | None = Field(
        None,
        description="New API key or OAuth token (will be encrypted). Omit to keep current.",
        min_length=1,
        max_length=500,
    )

    auth_type: AuthType | None = Field(
        None,
        description="Authentication type: 'api_key' or 'oauth_token'",
    )

    display_name: str | None = Field(
        None,
        description="New display name",
        max_length=255,
    )

    base_url: str | None = Field(
        None,
        description="New base URL (pass empty string to clear)",
    )

    is_active: bool | None = Field(
        None,
        description="Enable or disable the provider",
    )

    is_default: bool | None = Field(
        None,
        description="Set as default provider",
    )

    config: dict[str, Any] | None = Field(
        None,
        description="New configuration (replaces existing)",
    )


class AIProviderResponse(BaseModel):
    """Schema for AI provider response."""

    id: str = Field(..., description="Provider ID")
    provider_name: str = Field(..., description="Provider identifier")
    display_name: str = Field(..., description="User-friendly name")
    api_key_prefix: str = Field(
        ...,
        description="Masked credential prefix (e.g., 'sk-proj-...')",
    )
    auth_type: AuthType = Field(default="api_key", description="Authentication type: 'api_key' or 'oauth_token'")
    base_url: str | None = Field(None, description="Custom API endpoint")
    is_active: bool = Field(..., description="Whether the provider is enabled")
    is_default: bool = Field(..., description="Whether this is the default provider")
    config: dict[str, Any] = Field(default_factory=dict, description="Configuration")
    last_used_at: datetime | None = Field(
        None,
        description="Most recent successful use by the AI service",
    )
    created_at: datetime = Field(..., description="Creation time")
    updated_at: datetime = Field(..., description="Last update time")

    model_config = {"from_attributes": True}


class AIProvidersResponse(BaseModel):
    """Schema for listing AI providers."""

    providers: list[AIProviderResponse]
    total: int


class AIProviderTestResponse(BaseModel):
    """Schema for provider connectivity test result."""

    status: Literal["healthy", "error", "unknown"] = Field(
        ...,
        description="Test result status",
    )
    message: str = Field(..., description="Human-readable status message")
    model_tested: str | None = Field(None, description="Model used for testing")


class AIProviderRotateRequest(BaseModel):
    """Schema for rotating an API key."""

    new_api_key: str = Field(
        ...,
        description="The new API key",
        min_length=1,
        max_length=500,
    )


class KnownProviderInfo(BaseModel):
    """Information about a known AI provider."""

    name: str = Field(..., description="Provider identifier")
    display_name: str = Field(..., description="User-friendly name")
    models: list[str] = Field(default_factory=list, description="Available models")
    default_model: str | None = Field(None, description="Default model")


class KnownProvidersResponse(BaseModel):
    """List of known AI providers and their models."""

    providers: list[KnownProviderInfo]
