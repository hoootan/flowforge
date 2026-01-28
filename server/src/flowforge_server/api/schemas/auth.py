"""Pydantic schemas for authentication API operations."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ApiKeyCreate(BaseModel):
    """Schema for creating a new API key."""

    name: str = Field(
        ...,
        description="Human-readable name for the key",
        examples=["Production", "CI/CD", "Dashboard"],
        min_length=1,
        max_length=255,
    )

    key_type: Literal["live", "test", "ro"] = Field(
        default="test",
        description="Key type: 'live' for production, 'test' for testing, 'ro' for read-only",
    )

    scopes: list[str] | None = Field(
        None,
        description="Custom scopes (uses defaults for key type if not specified)",
        examples=[["events:send", "events:read", "runs:read"]],
    )

    expires_in_days: int | None = Field(
        None,
        description="Number of days until the key expires (None = never)",
        ge=1,
        le=365,
    )


class ApiKeyResponse(BaseModel):
    """Schema for API key response (without the raw key)."""

    id: str = Field(..., description="API key ID")
    name: str = Field(..., description="Human-readable name")
    key_prefix: str = Field(..., description="Key prefix for identification (e.g., ff_live_a1b2)")
    key_type: str = Field(..., description="Key type: live, test, or ro")
    scopes: list[str] = Field(..., description="Granted scopes")
    expires_at: datetime | None = Field(None, description="Expiration time")
    last_used_at: datetime | None = Field(None, description="Last usage time")
    is_active: bool = Field(..., description="Whether the key is active")
    created_at: datetime = Field(..., description="Creation time")

    model_config = {"from_attributes": True}


class ApiKeyCreatedResponse(ApiKeyResponse):
    """Response when a new API key is created (includes the raw key once)."""

    key: str = Field(
        ...,
        description="The full API key. Store this securely - it won't be shown again!",
        examples=["ff_live_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"],
    )


class ApiKeysResponse(BaseModel):
    """Schema for listing API keys."""

    keys: list[ApiKeyResponse]
    total: int


class TokenRequest(BaseModel):
    """Schema for requesting a JWT token."""

    api_key: str = Field(
        ...,
        description="API key to exchange for a JWT token",
        examples=["ff_live_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"],
    )

    expires_in: int = Field(
        default=3600,
        description="Token lifetime in seconds (default: 1 hour, max: 24 hours)",
        ge=60,
        le=86400,
    )


class TokenResponse(BaseModel):
    """Schema for JWT token response."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Token lifetime in seconds")
    expires_at: datetime = Field(..., description="Expiration timestamp")
    scopes: list[str] = Field(..., description="Scopes included in the token")


class RevokeApiKeyRequest(BaseModel):
    """Schema for revoking an API key."""

    reason: str | None = Field(
        None,
        description="Optional reason for revocation",
        max_length=500,
    )
