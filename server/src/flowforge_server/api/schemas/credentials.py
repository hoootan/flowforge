"""Pydantic schemas for credential-related API operations."""

from datetime import datetime

from pydantic import BaseModel, Field


class CredentialCreate(BaseModel):
    """Schema for creating a new credential."""

    name: str = Field(
        ...,
        description="Unique credential name (per tenant)",
        examples=["supabase_key"],
        min_length=1,
        max_length=255,
    )
    credential_type: str = Field(
        default="api_key",
        description="Type of credential",
        examples=["api_key", "bearer_token", "basic_auth", "custom"],
    )
    value: str = Field(
        ...,
        description="The secret value to encrypt and store",
        min_length=1,
    )
    description: str | None = Field(
        None,
        description="Optional description",
    )


class CredentialUpdate(BaseModel):
    """Schema for updating a credential."""

    value: str | None = Field(None, description="New secret value (re-encrypted)")
    description: str | None = Field(None, description="Updated description")
    credential_type: str | None = Field(None, description="Updated type")
    is_active: bool | None = Field(None, description="Active status")


class CredentialResponse(BaseModel):
    """Schema for credential API response (never includes decrypted value)."""

    id: str = Field(..., description="Credential ID")
    name: str = Field(..., description="Credential name")
    credential_type: str = Field(..., description="Credential type")
    value_prefix: str = Field(..., description="Masked value prefix")
    description: str | None = Field(None, description="Description")
    is_active: bool = Field(..., description="Whether active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {"from_attributes": True}


class CredentialsResponse(BaseModel):
    """Schema for listing credentials."""

    credentials: list[CredentialResponse]
    total: int
