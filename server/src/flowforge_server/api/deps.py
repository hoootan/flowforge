"""API dependencies for authentication and common patterns."""

import hashlib
from datetime import datetime, timezone
from typing import Annotated
import uuid

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge_server.config import get_settings, Settings
from flowforge_server.db import get_session
from flowforge_server.db.models import Tenant, ApiKey
from flowforge_server.db.models.user import User, UserRole


def hash_api_key(api_key: str) -> str:
    """Hash an API key using SHA-256."""
    return hashlib.sha256(api_key.encode()).hexdigest()


async def _validate_api_key_from_model(
    session: AsyncSession,
    api_key: str,
) -> tuple[ApiKey | None, Tenant | None]:
    """
    Validate API key against the ApiKey model.
    Returns (api_key_model, tenant) if valid, (None, None) if not found.
    """
    api_key_hash = hash_api_key(api_key)

    # Look up in api_keys table
    result = await session.execute(
        select(ApiKey).where(
            ApiKey.key_hash == api_key_hash,
            ApiKey.is_active == True,
        )
    )
    api_key_model = result.scalar_one_or_none()

    if not api_key_model:
        return None, None

    # Check expiration
    if api_key_model.expires_at and datetime.now(timezone.utc) > api_key_model.expires_at:
        return None, None

    # Update last_used_at
    await session.execute(
        update(ApiKey)
        .where(ApiKey.id == api_key_model.id)
        .values(last_used_at=datetime.now(timezone.utc))
    )

    # Load tenant
    result = await session.execute(
        select(Tenant).where(Tenant.id == api_key_model.tenant_id)
    )
    tenant = result.scalar_one_or_none()

    return api_key_model, tenant


async def _validate_jwt_token(
    session: AsyncSession,
    token: str,
    settings: Settings,
) -> Tenant | None:
    """
    Validate a JWT token and return the associated tenant.
    Returns None if the token is invalid.
    """
    jwt_secret = getattr(settings, 'jwt_secret', None)
    if not jwt_secret:
        return None

    try:
        import jwt
        payload = jwt.decode(token, jwt_secret, algorithms=["HS256"])

        # Check if this is a user token or API key token
        token_type = payload.get("type")

        if token_type == "user":
            # User token - get tenant from tenant_id field
            tenant_id = uuid.UUID(payload["tenant_id"])
        else:
            # API key token - get tenant from subject
            tenant_id = uuid.UUID(payload["sub"])

        result = await session.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        return result.scalar_one_or_none()

    except (ImportError, jwt.InvalidTokenError, KeyError, ValueError):
        return None


async def _validate_user_jwt_token(
    session: AsyncSession,
    token: str,
    settings: Settings,
) -> User | None:
    """
    Validate a user JWT token and return the User object.
    Returns None if the token is invalid or not a user token.
    """
    jwt_secret = getattr(settings, 'jwt_secret', None)
    if not jwt_secret:
        return None

    try:
        import jwt
        payload = jwt.decode(token, jwt_secret, algorithms=["HS256"])

        # Check this is a user token
        if payload.get("type") != "user":
            return None

        # Get user from subject (user_id)
        user_id = uuid.UUID(payload["sub"])

        result = await session.execute(
            select(User).where(User.id == user_id, User.is_active == True)
        )
        return result.scalar_one_or_none()

    except (ImportError, jwt.InvalidTokenError, KeyError, ValueError):
        return None


async def get_current_tenant(
    session: AsyncSession = Depends(get_session),
    api_key: str | None = Header(None, alias="X-FlowForge-API-Key"),
    authorization: str | None = Header(None),
    settings: Settings = Depends(get_settings),
) -> Tenant:
    """
    Authenticate request and return the current tenant.

    Supports two authentication methods:
    1. API Key: X-FlowForge-API-Key header (recommended for server-to-server)
    2. JWT Token: Authorization: Bearer <token> header (for CLI/dashboard)

    Raises:
        HTTPException(401): If authentication is missing or invalid
    """
    # Try API key first
    if api_key:
        # Try the new ApiKey model first
        api_key_model, tenant = await _validate_api_key_from_model(session, api_key)
        if tenant:
            return tenant

        # Fall back to legacy Tenant.api_key_hash for backwards compatibility
        api_key_hash = hash_api_key(api_key)
        result = await session.execute(
            select(Tenant).where(Tenant.api_key_hash == api_key_hash)
        )
        tenant = result.scalar_one_or_none()

        if tenant:
            return tenant

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Try JWT token
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        tenant = await _validate_jwt_token(session, token, settings)

        if tenant:
            return tenant

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing authentication. Provide X-FlowForge-API-Key header or Authorization: Bearer token.",
        headers={"WWW-Authenticate": "ApiKey"},
    )


async def get_optional_tenant(
    session: AsyncSession = Depends(get_session),
    api_key: str | None = Header(None, alias="X-FlowForge-API-Key"),
    authorization: str | None = Header(None),
    settings: Settings = Depends(get_settings),
) -> Tenant | None:
    """
    Optionally authenticate request and return the tenant if credentials provided.

    This is useful for endpoints that can work both authenticated and unauthenticated.
    Returns None if no credentials are provided, raises 401 if credentials are invalid.
    """
    # Try API key first
    if api_key:
        # Try the new ApiKey model first
        api_key_model, tenant = await _validate_api_key_from_model(session, api_key)
        if tenant:
            return tenant

        # Fall back to legacy Tenant.api_key_hash for backwards compatibility
        api_key_hash = hash_api_key(api_key)
        result = await session.execute(
            select(Tenant).where(Tenant.api_key_hash == api_key_hash)
        )
        tenant = result.scalar_one_or_none()

        if tenant:
            return tenant

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Try JWT token
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        tenant = await _validate_jwt_token(session, token, settings)

        if tenant:
            return tenant

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return None


# Development fallback tenant ID
DEFAULT_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def get_tenant_with_dev_fallback(
    session: AsyncSession = Depends(get_session),
    api_key: str | None = Header(None, alias="X-FlowForge-API-Key"),
    authorization: str | None = Header(None),
    settings: Settings = Depends(get_settings),
) -> Tenant:
    """
    Get current tenant with development fallback.

    In development mode, if no credentials are provided, falls back to the default tenant.
    In production, always requires authentication.

    Supports two authentication methods:
    1. API Key: X-FlowForge-API-Key header (recommended for server-to-server)
    2. JWT Token: Authorization: Bearer <token> header (for CLI/dashboard)
    """
    # Try API key first
    if api_key:
        # Try the new ApiKey model first
        api_key_model, tenant = await _validate_api_key_from_model(session, api_key)
        if tenant:
            return tenant

        # Fall back to legacy Tenant.api_key_hash for backwards compatibility
        api_key_hash = hash_api_key(api_key)
        result = await session.execute(
            select(Tenant).where(Tenant.api_key_hash == api_key_hash)
        )
        tenant = result.scalar_one_or_none()

        if tenant:
            return tenant

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Try JWT token
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        tenant = await _validate_jwt_token(session, token, settings)

        if tenant:
            return tenant

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # No credentials provided
    if settings.is_development:
        # In development, fall back to default tenant
        result = await session.execute(
            select(Tenant).where(Tenant.id == DEFAULT_TENANT_ID)
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Default tenant not found. Run database seeds.",
            )
        return tenant

    # Production requires authentication
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing authentication. Provide X-FlowForge-API-Key header or Authorization: Bearer token.",
        headers={"WWW-Authenticate": "ApiKey"},
    )


# Type aliases for dependency injection
CurrentTenant = Annotated[Tenant, Depends(get_current_tenant)]
OptionalTenant = Annotated[Tenant | None, Depends(get_optional_tenant)]
TenantWithDevFallback = Annotated[Tenant, Depends(get_tenant_with_dev_fallback)]


# User authentication dependencies

async def get_current_user(
    session: AsyncSession = Depends(get_session),
    authorization: str | None = Header(None),
    settings: Settings = Depends(get_settings),
) -> User:
    """
    Authenticate request and return the current user.

    Only accepts JWT tokens from user login (not API key tokens).

    Raises:
        HTTPException(401): If authentication is missing or invalid
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication. Provide Authorization: Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization[7:]
    user = await _validate_user_jwt_token(session, token, settings)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_optional_user(
    session: AsyncSession = Depends(get_session),
    authorization: str | None = Header(None),
    settings: Settings = Depends(get_settings),
) -> User | None:
    """
    Optionally authenticate request and return the user if credentials provided.

    Returns None if no credentials are provided, raises 401 if credentials are invalid.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization[7:]
    user = await _validate_user_jwt_token(session, token, settings)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_role(allowed_roles: list[UserRole]):
    """
    Create a dependency that checks if the user has one of the required roles.

    Usage:
        @router.post("/users")
        async def create_user(
            user: Annotated[User, Depends(require_role([UserRole.ADMIN]))]
        ):
            ...
    """
    async def check_role(
        session: AsyncSession = Depends(get_session),
        authorization: str | None = Header(None),
        settings: Settings = Depends(get_settings),
    ) -> User:
        user = await get_current_user(session, authorization, settings)

        user_role = UserRole(user.role)
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return user

    return check_role


async def get_admin_user(
    session: AsyncSession = Depends(get_session),
    authorization: str | None = Header(None),
    settings: Settings = Depends(get_settings),
) -> User:
    """
    Get the current user and verify they have admin role.

    Raises:
        HTTPException(401): If not authenticated
        HTTPException(403): If not an admin
    """
    user = await get_current_user(session, authorization, settings)

    if user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return user


# Type aliases for user authentication
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
CurrentUserAdmin = Annotated[User, Depends(get_admin_user)]
