"""Pydantic schemas for user management API operations."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, EmailStr


class UserLogin(BaseModel):
    """Schema for user login request."""

    email: EmailStr = Field(
        ...,
        description="User email address",
        examples=["admin@example.com"],
    )

    password: str = Field(
        ...,
        description="User password",
        min_length=1,
    )


class UserLoginResponse(BaseModel):
    """Schema for successful login response."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Token lifetime in seconds")
    expires_at: datetime = Field(..., description="Expiration timestamp")
    user: "UserResponse" = Field(..., description="User details")


class User2FARequiredResponse(BaseModel):
    """Schema for login response when 2FA is required."""

    requires_2fa: bool = Field(default=True, description="Whether 2FA is required")
    temp_token: str = Field(..., description="Temporary token for 2FA verification")


class Verify2FARequest(BaseModel):
    """Schema for 2FA verification request."""

    temp_token: str = Field(..., description="Temporary token from login")
    code: str = Field(
        ...,
        description="6-digit TOTP code or backup code",
        min_length=1,
        max_length=20,
    )


class Setup2FAResponse(BaseModel):
    """Schema for 2FA setup response."""

    secret: str = Field(..., description="TOTP secret (base32)")
    qr_code: str = Field(..., description="Base64-encoded QR code image")


class Confirm2FARequest(BaseModel):
    """Schema for 2FA confirmation request."""

    code: str = Field(
        ...,
        description="6-digit TOTP code to confirm setup",
        min_length=6,
        max_length=6,
    )


class Confirm2FAResponse(BaseModel):
    """Schema for 2FA confirmation response."""

    success: bool = Field(default=True, description="Whether 2FA was enabled")
    backup_codes: list[str] = Field(..., description="Backup codes for recovery")


class Disable2FARequest(BaseModel):
    """Schema for 2FA disable request."""

    password: str = Field(
        ...,
        description="Current password for verification",
        min_length=1,
    )


class BackupCodesRequest(BaseModel):
    """Schema for backup codes request."""

    password: str = Field(
        ...,
        description="Current password for verification",
        min_length=1,
    )


class BackupCodesResponse(BaseModel):
    """Schema for backup codes response."""

    backup_codes: list[str] = Field(..., description="Backup codes")


class UserCreate(BaseModel):
    """Schema for creating a new user."""

    email: EmailStr = Field(
        ...,
        description="User email address",
        examples=["user@example.com"],
    )

    password: str = Field(
        ...,
        description="User password",
        min_length=8,
        max_length=128,
    )

    name: str = Field(
        ...,
        description="User display name",
        min_length=1,
        max_length=255,
        examples=["John Doe"],
    )

    role: Literal["admin", "member", "viewer"] = Field(
        default="member",
        description="User role: admin, member, or viewer",
    )


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    email: EmailStr | None = Field(
        None,
        description="New email address",
    )

    name: str | None = Field(
        None,
        description="New display name",
        min_length=1,
        max_length=255,
    )

    role: Literal["admin", "member", "viewer"] | None = Field(
        None,
        description="New role",
    )

    is_active: bool | None = Field(
        None,
        description="Whether the user is active",
    )


class UserPasswordUpdate(BaseModel):
    """Schema for updating user password."""

    current_password: str = Field(
        ...,
        description="Current password for verification",
        min_length=1,
    )

    new_password: str = Field(
        ...,
        description="New password",
        min_length=8,
        max_length=128,
    )


class UserResponse(BaseModel):
    """Schema for user response."""

    id: str = Field(..., description="User ID")
    email: str = Field(..., description="Email address")
    name: str = Field(..., description="Display name")
    role: str = Field(..., description="User role")
    is_active: bool = Field(..., description="Whether the user is active")
    last_login_at: datetime | None = Field(None, description="Last login timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = {"from_attributes": True}


class UsersResponse(BaseModel):
    """Schema for listing users."""

    users: list[UserResponse]
    total: int


class UserMeResponse(BaseModel):
    """Schema for current user response with additional info."""

    id: str = Field(..., description="User ID")
    email: str = Field(..., description="Email address")
    name: str = Field(..., description="Display name")
    role: str = Field(..., description="User role")
    is_active: bool = Field(..., description="Whether the user is active")
    last_login_at: datetime | None = Field(None, description="Last login timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    tenant_id: str = Field(..., description="Tenant ID")
    permissions: dict = Field(..., description="User permissions")
    totp_enabled: bool = Field(default=False, description="Whether 2FA is enabled")

    model_config = {"from_attributes": True}


# Update forward reference
UserLoginResponse.model_rebuild()
