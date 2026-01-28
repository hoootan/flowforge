"""Authentication service for API key and JWT management."""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge_server.db.models import ApiKey, ApiKeyType, Tenant, DEFAULT_SCOPES, ALL_SCOPES


# API key configuration
API_KEY_PREFIX = "ff"
API_KEY_RANDOM_BYTES = 24  # 32 characters when base64-encoded


def generate_api_key(key_type: ApiKeyType = ApiKeyType.TEST) -> tuple[str, str, str]:
    """
    Generate a new API key.

    Returns:
        Tuple of (full_key, key_hash, key_prefix)
        - full_key: The complete API key (ff_test_xxx...)
        - key_hash: SHA-256 hash of the full key for storage
        - key_prefix: First 12 chars for identification (ff_test_a1b2)
    """
    # Generate random bytes and encode as hex
    random_part = secrets.token_hex(API_KEY_RANDOM_BYTES)

    # Build the full key: ff_{type}_{random}
    full_key = f"{API_KEY_PREFIX}_{key_type.value}_{random_part}"

    # Hash for storage
    key_hash = hash_api_key(full_key)

    # Prefix for identification (first 12 chars including the type prefix)
    key_prefix = full_key[:16]  # e.g., "ff_test_a1b2c3d4"

    return full_key, key_hash, key_prefix


def hash_api_key(api_key: str) -> str:
    """Hash an API key using SHA-256."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def parse_api_key(api_key: str) -> tuple[str, ApiKeyType | None]:
    """
    Parse an API key to extract its type.

    Returns:
        Tuple of (random_part, key_type)
        key_type is None if the key format is invalid.
    """
    parts = api_key.split("_", 2)
    if len(parts) != 3 or parts[0] != API_KEY_PREFIX:
        return api_key, None

    prefix, type_str, random_part = parts

    try:
        key_type = ApiKeyType(type_str)
        return random_part, key_type
    except ValueError:
        return api_key, None


def get_default_scopes(key_type: ApiKeyType) -> list[str]:
    """Get default scopes for a key type."""
    return DEFAULT_SCOPES.get(key_type, [])


def validate_scopes(scopes: list[str]) -> list[str]:
    """Validate and normalize scopes, returning only valid ones."""
    return [s for s in scopes if s in ALL_SCOPES]


def has_scope(api_key: ApiKey, required_scope: str) -> bool:
    """Check if an API key has a specific scope."""
    # Admin scope grants everything
    if "admin" in api_key.scopes:
        return True
    return required_scope in api_key.scopes


def has_any_scope(api_key: ApiKey, required_scopes: list[str]) -> bool:
    """Check if an API key has any of the required scopes."""
    if "admin" in api_key.scopes:
        return True
    return any(scope in api_key.scopes for scope in required_scopes)


def has_all_scopes(api_key: ApiKey, required_scopes: list[str]) -> bool:
    """Check if an API key has all of the required scopes."""
    if "admin" in api_key.scopes:
        return True
    return all(scope in api_key.scopes for scope in required_scopes)


async def create_api_key(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    name: str,
    key_type: ApiKeyType = ApiKeyType.TEST,
    scopes: list[str] | None = None,
    expires_in_days: int | None = None,
) -> tuple[ApiKey, str]:
    """
    Create a new API key for a tenant.

    Returns:
        Tuple of (ApiKey model, raw key string)
        The raw key is only returned once and should be shown to the user.
    """
    # Generate the key
    full_key, key_hash, key_prefix = generate_api_key(key_type)

    # Use default scopes if not specified
    if scopes is None:
        scopes = get_default_scopes(key_type)
    else:
        scopes = validate_scopes(scopes)

    # Calculate expiration
    expires_at = None
    if expires_in_days is not None:
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

    # Create the model
    api_key = ApiKey(
        tenant_id=tenant_id,
        name=name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        key_type=key_type.value,
        scopes=scopes,
        expires_at=expires_at,
    )

    session.add(api_key)
    await session.flush()

    return api_key, full_key


async def get_api_key_by_hash(session: AsyncSession, key_hash: str) -> ApiKey | None:
    """Look up an API key by its hash."""
    result = await session.execute(
        select(ApiKey).where(
            ApiKey.key_hash == key_hash,
            ApiKey.is_active == True,
        )
    )
    return result.scalar_one_or_none()


async def validate_api_key(
    session: AsyncSession,
    raw_key: str,
    required_scope: str | None = None,
) -> tuple[ApiKey | None, Tenant | None, str | None]:
    """
    Validate an API key and return the associated tenant.

    Returns:
        Tuple of (api_key, tenant, error_message)
        If valid, error_message is None.
        If invalid, api_key and tenant are None, error_message explains why.
    """
    key_hash = hash_api_key(raw_key)

    result = await session.execute(
        select(ApiKey)
        .where(ApiKey.key_hash == key_hash)
    )
    api_key = result.scalar_one_or_none()

    if api_key is None:
        return None, None, "Invalid API key"

    if not api_key.is_active:
        return None, None, "API key has been revoked"

    if api_key.is_expired:
        return None, None, "API key has expired"

    # Check scope if required
    if required_scope and not has_scope(api_key, required_scope):
        return None, None, f"API key lacks required scope: {required_scope}"

    # Update last_used_at
    await session.execute(
        update(ApiKey)
        .where(ApiKey.id == api_key.id)
        .values(last_used_at=datetime.now(timezone.utc))
    )

    # Load tenant
    result = await session.execute(
        select(Tenant).where(Tenant.id == api_key.tenant_id)
    )
    tenant = result.scalar_one_or_none()

    if tenant is None:
        return None, None, "Tenant not found"

    return api_key, tenant, None


async def revoke_api_key(
    session: AsyncSession,
    api_key_id: uuid.UUID,
    reason: str | None = None,
) -> bool:
    """Revoke an API key."""
    result = await session.execute(
        update(ApiKey)
        .where(ApiKey.id == api_key_id)
        .values(
            is_active=False,
            revoked_at=datetime.now(timezone.utc),
            revoked_reason=reason,
        )
        .returning(ApiKey.id)
    )
    return result.scalar_one_or_none() is not None


async def list_api_keys(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    include_revoked: bool = False,
) -> list[ApiKey]:
    """List all API keys for a tenant."""
    query = select(ApiKey).where(ApiKey.tenant_id == tenant_id)

    if not include_revoked:
        query = query.where(ApiKey.is_active == True)

    query = query.order_by(ApiKey.created_at.desc())

    result = await session.execute(query)
    return list(result.scalars().all())
