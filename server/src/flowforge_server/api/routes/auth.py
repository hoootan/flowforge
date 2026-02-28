"""Authentication and API key management endpoints."""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge_server.api.deps import TenantWithDevFallback
from flowforge_server.api.schemas.auth import (
    ApiKeyCreate,
    ApiKeyCreatedResponse,
    ApiKeyResponse,
    ApiKeysResponse,
    RevokeApiKeyRequest,
    TokenRequest,
    TokenResponse,
)
from flowforge_server.db import get_session
from flowforge_server.db.models import ApiKey, ApiKeyType
from flowforge_server.services.auth import (
    create_api_key,
    list_api_keys,
    revoke_api_key,
    validate_api_key,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def api_key_to_response(api_key: ApiKey) -> ApiKeyResponse:
    """Convert ApiKey model to response schema."""
    return ApiKeyResponse(
        id=str(api_key.id),
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        key_type=api_key.key_type,
        scopes=api_key.scopes,
        expires_at=api_key.expires_at,
        last_used_at=api_key.last_used_at,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
    )


@router.get("/keys", response_model=ApiKeysResponse)
async def list_keys(
    tenant: TenantWithDevFallback,
    include_revoked: bool = False,
    session: AsyncSession = Depends(get_session),
) -> ApiKeysResponse:
    """
    List all API keys for the current tenant.

    By default, only active keys are returned. Set `include_revoked=true`
    to include revoked keys.
    """
    keys = await list_api_keys(session, tenant.id, include_revoked=include_revoked)

    return ApiKeysResponse(
        keys=[api_key_to_response(key) for key in keys],
        total=len(keys),
    )


@router.post("/keys", response_model=ApiKeyCreatedResponse, status_code=201)
async def create_key(
    key_data: ApiKeyCreate,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> ApiKeyCreatedResponse:
    """
    Create a new API key.

    The raw key is only returned once in this response. Store it securely!

    **Key types:**
    - `live`: Full access for production use
    - `test`: Full access for testing/development
    - `ro`: Read-only access

    **Scopes:** If not specified, default scopes for the key type are used.
    Available scopes:
    - `events:send`, `events:read`
    - `runs:read`, `runs:manage`
    - `functions:read`, `functions:manage`
    - `tools:read`, `tools:manage`
    - `approvals:read`, `approvals:manage`
    - `admin` (full access)
    """
    # Convert key_type string to enum
    try:
        key_type = ApiKeyType(key_data.key_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid key type: {key_data.key_type}. Must be 'live', 'test', or 'ro'",
        )

    api_key, raw_key = await create_api_key(
        session=session,
        tenant_id=tenant.id,
        name=key_data.name,
        key_type=key_type,
        scopes=key_data.scopes,
        expires_in_days=key_data.expires_in_days,
    )

    await session.commit()

    return ApiKeyCreatedResponse(
        id=str(api_key.id),
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        key_type=api_key.key_type,
        scopes=api_key.scopes,
        expires_at=api_key.expires_at,
        last_used_at=api_key.last_used_at,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        key=raw_key,
    )


@router.get("/keys/{key_id}", response_model=ApiKeyResponse)
async def get_key(
    key_id: str,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> ApiKeyResponse:
    """Get details of a specific API key."""
    try:
        key_uuid = uuid.UUID(key_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid key ID format")

    result = await session.execute(
        select(ApiKey).where(
            ApiKey.id == key_uuid,
            ApiKey.tenant_id == tenant.id,
        )
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    return api_key_to_response(api_key)


@router.delete("/keys/{key_id}", status_code=204)
async def delete_key(
    key_id: str,
    tenant: TenantWithDevFallback,
    revoke_data: RevokeApiKeyRequest | None = None,
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    Revoke an API key.

    Revoked keys can no longer be used for authentication.
    This action cannot be undone.
    """
    try:
        key_uuid = uuid.UUID(key_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid key ID format")

    # Verify the key belongs to this tenant
    result = await session.execute(
        select(ApiKey).where(
            ApiKey.id == key_uuid,
            ApiKey.tenant_id == tenant.id,
        )
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    reason = revoke_data.reason if revoke_data else None
    await revoke_api_key(session, key_uuid, reason=reason)
    await session.commit()


@router.post("/token", response_model=TokenResponse)
async def create_token(
    token_request: TokenRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """
    Exchange an API key for a short-lived JWT token.

    JWT tokens are useful for:
    - CLI sessions
    - Dashboard authentication
    - Short-lived operations where you don't want to expose the API key

    The token includes the same scopes as the API key.
    """
    # Validate the API key
    api_key, tenant, error = await validate_api_key(session, token_request.api_key)

    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error,
        )

    # Import here to avoid circular imports and to make JWT optional
    try:
        import jwt
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="JWT support not available. Install PyJWT: pip install pyjwt",
        )

    from flowforge_server.config import get_settings
    settings = get_settings()

    # Get JWT secret (will be added in Phase 3)
    jwt_secret = getattr(settings, 'jwt_secret', None)
    if not jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="JWT support not configured. Set FLOWFORGE_JWT_SECRET environment variable.",
        )

    # Calculate expiration
    expires_at = datetime.now(UTC) + timedelta(seconds=token_request.expires_in)

    # Create token payload
    payload = {
        "sub": str(tenant.id),  # Subject is tenant ID
        "key_id": str(api_key.id),
        "scopes": api_key.scopes,
        "iat": datetime.now(UTC),
        "exp": expires_at,
    }

    # Generate token
    access_token = jwt.encode(payload, jwt_secret, algorithm="HS256")

    await session.commit()

    return TokenResponse(
        access_token=access_token,
        token_type="Bearer",
        expires_in=token_request.expires_in,
        expires_at=expires_at,
        scopes=api_key.scopes,
    )


@router.post("/revoke", status_code=204)
async def revoke_token() -> None:
    """
    Revoke a JWT token.

    Note: JWT tokens are stateless and cannot truly be revoked.
    This endpoint is provided for API consistency but the token
    will remain valid until it expires.

    For immediate revocation, revoke the underlying API key instead.
    """
    # JWT tokens are stateless - we could implement a token blacklist
    # but for now we just acknowledge the request
    pass
