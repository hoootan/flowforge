"""User service for authentication and user management."""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge_server.db.models.user import User, UserRole
from flowforge_server.db.models.tenant import Tenant
from flowforge_server.config import get_settings


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Falls back to SHA-256 if bcrypt is not available.
    """
    try:
        import bcrypt
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode(), salt).decode()
    except ImportError:
        # Fallback to SHA-256 with salt (less secure but works without bcrypt)
        salt = secrets.token_hex(16)
        hash_value = hashlib.sha256((salt + password).encode()).hexdigest()
        return f"sha256${salt}${hash_value}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    if password_hash.startswith("sha256$"):
        # SHA-256 fallback
        _, salt, stored_hash = password_hash.split("$")
        computed_hash = hashlib.sha256((salt + password).encode()).hexdigest()
        return computed_hash == stored_hash

    try:
        import bcrypt
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ImportError:
        return False


def create_user_jwt(
    user: User,
    expires_in_seconds: int | None = None,
) -> str:
    """
    Create a JWT token for a user.

    Token payload includes:
    - sub: user_id
    - tenant_id: tenant_id
    - role: user role
    - email: user email
    - exp: expiration timestamp
    """
    settings = get_settings()

    if not settings.jwt_secret:
        raise ValueError("JWT_SECRET not configured")

    try:
        import jwt
    except ImportError:
        raise ImportError("PyJWT is required for user authentication. Install with: pip install pyjwt")

    if expires_in_seconds is None:
        expires_in_seconds = settings.jwt_default_expiry_seconds

    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)

    payload = {
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id),
        "role": user.role,
        "email": user.email,
        "name": user.name,
        "type": "user",  # Distinguish from API key tokens
        "iat": datetime.now(timezone.utc),
        "exp": expires_at,
    }

    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_user_jwt(token: str) -> dict | None:
    """
    Decode and validate a user JWT token.

    Returns the payload dict if valid, None if invalid.
    """
    settings = get_settings()

    if not settings.jwt_secret:
        return None

    try:
        import jwt
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        # Verify this is a user token
        if payload.get("type") != "user":
            return None
        return payload
    except (ImportError, Exception):
        return None


async def create_user(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    email: str,
    password: str,
    name: str,
    role: UserRole = UserRole.MEMBER,
) -> User:
    """
    Create a new user.

    Raises:
        ValueError: If a user with this email already exists for the tenant.
    """
    # Check for existing user with same email in tenant
    existing = await get_user_by_email(session, tenant_id, email)
    if existing:
        raise ValueError(f"User with email {email} already exists")

    user = User(
        tenant_id=tenant_id,
        email=email.lower(),
        password_hash=hash_password(password),
        name=name,
        role=role.value,
    )

    session.add(user)
    await session.flush()

    return user


async def get_user_by_id(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> User | None:
    """Get a user by ID."""
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def get_user_by_email(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    email: str,
) -> User | None:
    """Get a user by email within a tenant."""
    result = await session.execute(
        select(User).where(
            User.tenant_id == tenant_id,
            User.email == email.lower(),
        )
    )
    return result.scalar_one_or_none()


async def authenticate_user(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    email: str,
    password: str,
) -> tuple[User | None, str | None]:
    """
    Authenticate a user by email and password.

    Returns:
        Tuple of (user, error_message).
        If successful, error_message is None.
        If failed, user is None and error_message explains why.
    """
    user = await get_user_by_email(session, tenant_id, email)

    if not user:
        return None, "Invalid email or password"

    if not user.is_active:
        return None, "Account is deactivated"

    if not verify_password(password, user.password_hash):
        return None, "Invalid email or password"

    # Update last login
    await session.execute(
        update(User)
        .where(User.id == user.id)
        .values(last_login_at=datetime.now(timezone.utc))
    )

    return user, None


async def authenticate_user_any_tenant(
    session: AsyncSession,
    email: str,
    password: str,
) -> tuple[User | None, str | None]:
    """
    Authenticate a user by email and password across any tenant.

    This is used for login when the tenant is not known upfront.

    Returns:
        Tuple of (user, error_message).
    """
    result = await session.execute(
        select(User).where(
            User.email == email.lower(),
            User.is_active == True,
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        return None, "Invalid email or password"

    if not verify_password(password, user.password_hash):
        return None, "Invalid email or password"

    # Update last login
    await session.execute(
        update(User)
        .where(User.id == user.id)
        .values(last_login_at=datetime.now(timezone.utc))
    )

    return user, None


async def update_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    **kwargs,
) -> User | None:
    """
    Update a user's attributes.

    Supported fields: name, email, role, is_active.
    Use update_user_password for password changes.
    """
    user = await get_user_by_id(session, user_id)
    if not user:
        return None

    allowed_fields = {"name", "email", "role", "is_active"}
    update_data = {k: v for k, v in kwargs.items() if k in allowed_fields and v is not None}

    if "email" in update_data:
        update_data["email"] = update_data["email"].lower()

    if "role" in update_data:
        # Ensure role is a valid string
        if isinstance(update_data["role"], UserRole):
            update_data["role"] = update_data["role"].value

    if update_data:
        await session.execute(
            update(User)
            .where(User.id == user_id)
            .values(**update_data)
        )
        await session.flush()

        # Refresh the user object
        await session.refresh(user)

    return user


async def update_user_password(
    session: AsyncSession,
    user_id: uuid.UUID,
    new_password: str,
) -> bool:
    """Update a user's password."""
    result = await session.execute(
        update(User)
        .where(User.id == user_id)
        .values(password_hash=hash_password(new_password))
        .returning(User.id)
    )
    return result.scalar_one_or_none() is not None


async def delete_user(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> bool:
    """Delete a user (hard delete)."""
    user = await get_user_by_id(session, user_id)
    if not user:
        return False

    await session.delete(user)
    return True


async def deactivate_user(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> bool:
    """Deactivate a user (soft delete)."""
    result = await session.execute(
        update(User)
        .where(User.id == user_id)
        .values(is_active=False)
        .returning(User.id)
    )
    return result.scalar_one_or_none() is not None


async def list_users(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    include_inactive: bool = False,
) -> list[User]:
    """List all users for a tenant."""
    query = select(User).where(User.tenant_id == tenant_id)

    if not include_inactive:
        query = query.where(User.is_active == True)

    query = query.order_by(User.created_at.desc())

    result = await session.execute(query)
    return list(result.scalars().all())


async def count_users(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    include_inactive: bool = False,
) -> int:
    """Count users for a tenant."""
    query = select(func.count(User.id)).where(User.tenant_id == tenant_id)

    if not include_inactive:
        query = query.where(User.is_active == True)

    result = await session.execute(query)
    return result.scalar() or 0


async def count_admins(
    session: AsyncSession,
    tenant_id: uuid.UUID,
) -> int:
    """Count admin users for a tenant."""
    result = await session.execute(
        select(func.count(User.id)).where(
            User.tenant_id == tenant_id,
            User.role == UserRole.ADMIN.value,
            User.is_active == True,
        )
    )
    return result.scalar() or 0
