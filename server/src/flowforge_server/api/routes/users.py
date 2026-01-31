"""User management and authentication endpoints."""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update as sql_update

from flowforge_server.db import get_session
from flowforge_server.db.models.user import User, UserRole
from flowforge_server.config import get_settings, Settings
from flowforge_server.api.schemas.users import (
    UserLogin,
    UserLoginResponse,
    User2FARequiredResponse,
    Verify2FARequest,
    Setup2FAResponse,
    Confirm2FARequest,
    Confirm2FAResponse,
    Disable2FARequest,
    BackupCodesRequest,
    BackupCodesResponse,
    UserCreate,
    UserUpdate,
    UserPasswordUpdate,
    UserResponse,
    UsersResponse,
    UserMeResponse,
)
from flowforge_server.api.deps import (
    DEFAULT_TENANT_ID,
    CurrentUser,
    CurrentUserAdmin,
)
from flowforge_server.services.user import (
    authenticate_user_any_tenant,
    create_user,
    create_user_jwt,
    get_user_by_id,
    list_users,
    update_user,
    update_user_password,
    delete_user,
    count_admins,
    verify_password,
)
from flowforge_server.services.totp import (
    setup_totp_for_user,
    verify_totp_code,
    verify_backup_code,
    generate_backup_codes,
    encrypt_totp_secret,
    decrypt_totp_secret,
    encrypt_backup_codes,
)

router = APIRouter(prefix="/users", tags=["users"])


def create_temp_token(user: User, settings: Settings) -> str:
    """
    Create a temporary token for 2FA verification.

    This token is short-lived and can only be used to complete 2FA.
    """
    try:
        import jwt
    except ImportError:
        raise ImportError("PyJWT is required for user authentication. Install with: pip install pyjwt")

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    payload = {
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id),
        "type": "2fa_temp",
        "iat": datetime.now(timezone.utc),
        "exp": expires_at,
    }

    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_temp_token(token: str, settings: Settings) -> dict | None:
    """
    Decode and validate a temporary 2FA token.

    Returns the payload dict if valid, None if invalid.
    """
    try:
        import jwt
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        # Verify this is a temp token
        if payload.get("type") != "2fa_temp":
            return None
        return payload
    except Exception:
        return None


def user_to_response(user: User) -> UserResponse:
    """Convert User model to response schema."""
    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


@router.post("/login", response_model=UserLoginResponse | User2FARequiredResponse)
async def login(
    credentials: UserLogin,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> UserLoginResponse | User2FARequiredResponse:
    """
    Authenticate a user and return a JWT token.

    If the user has 2FA enabled, returns a temporary token that must be
    verified with the /users/verify-2fa endpoint.

    The token can be used in the Authorization header as:
    `Authorization: Bearer <token>`
    """
    user, error = await authenticate_user_any_tenant(
        session,
        credentials.email,
        credentials.password,
    )

    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error,
            headers={"WWW-Authenticate": "Bearer"},
        )

    await session.commit()

    # Check if 2FA is enabled
    if user.totp_enabled:
        # Return temporary token for 2FA verification
        temp_token = create_temp_token(user, settings)
        return User2FARequiredResponse(
            requires_2fa=True,
            temp_token=temp_token,
        )

    # No 2FA - return full login response
    expires_in = settings.jwt_default_expiry_seconds
    token = create_user_jwt(user, expires_in)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    return UserLoginResponse(
        access_token=token,
        token_type="Bearer",
        expires_in=expires_in,
        expires_at=expires_at,
        user=user_to_response(user),
    )


@router.post("/logout", status_code=204)
async def logout() -> None:
    """
    Log out the current user.

    Note: JWT tokens are stateless and cannot be truly invalidated.
    This endpoint is provided for API consistency. The client should
    discard the token on logout.
    """
    # JWT tokens are stateless - client should discard the token
    pass


@router.post("/verify-2fa", response_model=UserLoginResponse)
async def verify_2fa(
    request: Verify2FARequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> UserLoginResponse:
    """
    Verify 2FA code and complete login.

    Uses the temporary token from login and a TOTP code or backup code.
    """
    # Decode and validate temp token
    payload = decode_temp_token(request.temp_token, settings)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired verification token",
        )

    # Get user
    user_id = uuid.UUID(payload["sub"])
    user = await get_user_by_id(session, user_id)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    if not user.totp_enabled or not user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled for this user",
        )

    # Try TOTP code first
    decrypted_secret = decrypt_totp_secret(user.totp_secret)
    code_valid = verify_totp_code(decrypted_secret, request.code)

    # If TOTP fails, try backup code
    backup_code_used = False
    backup_code_index = None
    if not code_valid and user.backup_codes:
        code_valid, backup_code_index = verify_backup_code(request.code, user.backup_codes)
        backup_code_used = code_valid

    if not code_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid verification code",
        )

    # If backup code was used, remove it from the list
    if backup_code_used and backup_code_index is not None:
        new_backup_codes = user.backup_codes.copy()
        new_backup_codes.pop(backup_code_index)
        await session.execute(
            sql_update(User)
            .where(User.id == user.id)
            .values(backup_codes=new_backup_codes)
        )
        await session.commit()

    # Create full JWT token
    expires_in = settings.jwt_default_expiry_seconds
    token = create_user_jwt(user, expires_in)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    return UserLoginResponse(
        access_token=token,
        token_type="Bearer",
        expires_in=expires_in,
        expires_at=expires_at,
        user=user_to_response(user),
    )


@router.post("/2fa/setup", response_model=Setup2FAResponse)
async def setup_2fa(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> Setup2FAResponse:
    """
    Start 2FA setup for the current user.

    Returns a QR code and secret to configure an authenticator app.
    The setup must be confirmed with the /2fa/confirm endpoint.
    """
    if current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is already enabled. Disable it first to reconfigure.",
        )

    # Generate new TOTP setup
    setup_data = setup_totp_for_user(current_user.email)

    # Store encrypted secret temporarily (not enabled yet)
    encrypted_secret = encrypt_totp_secret(setup_data.secret)
    await session.execute(
        sql_update(User)
        .where(User.id == current_user.id)
        .values(totp_secret=encrypted_secret)
    )
    await session.commit()

    return Setup2FAResponse(
        secret=setup_data.secret,
        qr_code=setup_data.qr_code,
    )


@router.post("/2fa/confirm", response_model=Confirm2FAResponse)
async def confirm_2fa(
    request: Confirm2FARequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> Confirm2FAResponse:
    """
    Confirm 2FA setup with a verification code.

    This enables 2FA and returns backup codes.
    """
    if current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is already enabled",
        )

    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA setup not started. Call /2fa/setup first.",
        )

    # Verify the code
    decrypted_secret = decrypt_totp_secret(current_user.totp_secret)
    if not verify_totp_code(decrypted_secret, request.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code",
        )

    # Generate backup codes
    backup_codes = generate_backup_codes()
    hashed_backup_codes = encrypt_backup_codes(backup_codes)

    # Enable 2FA
    await session.execute(
        sql_update(User)
        .where(User.id == current_user.id)
        .values(
            totp_enabled=True,
            backup_codes=hashed_backup_codes,
        )
    )
    await session.commit()

    return Confirm2FAResponse(
        success=True,
        backup_codes=backup_codes,
    )


@router.post("/2fa/disable", status_code=204)
async def disable_2fa(
    request: Disable2FARequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    Disable 2FA for the current user.

    Requires password verification.
    """
    if not current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled",
        )

    # Verify password
    if not verify_password(request.password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid password",
        )

    # Disable 2FA
    await session.execute(
        sql_update(User)
        .where(User.id == current_user.id)
        .values(
            totp_enabled=False,
            totp_secret=None,
            backup_codes=None,
        )
    )
    await session.commit()


@router.post("/2fa/backup-codes", response_model=BackupCodesResponse)
async def get_backup_codes(
    request: BackupCodesRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> BackupCodesResponse:
    """
    View remaining backup codes.

    Requires password verification.
    Note: This returns masked versions for security.
    """
    if not current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled",
        )

    # Verify password
    if not verify_password(request.password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid password",
        )

    # Return count of remaining codes (we can't retrieve the original codes)
    remaining_count = len(current_user.backup_codes) if current_user.backup_codes else 0

    return BackupCodesResponse(
        backup_codes=[f"***-**** ({remaining_count} remaining)"],
    )


@router.post("/2fa/regenerate-backup-codes", response_model=BackupCodesResponse)
async def regenerate_backup_codes(
    request: BackupCodesRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> BackupCodesResponse:
    """
    Regenerate backup codes.

    This invalidates all existing backup codes and generates new ones.
    Requires password verification.
    """
    if not current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled",
        )

    # Verify password
    if not verify_password(request.password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid password",
        )

    # Generate new backup codes
    backup_codes = generate_backup_codes()
    hashed_backup_codes = encrypt_backup_codes(backup_codes)

    # Update backup codes
    await session.execute(
        sql_update(User)
        .where(User.id == current_user.id)
        .values(backup_codes=hashed_backup_codes)
    )
    await session.commit()

    return BackupCodesResponse(
        backup_codes=backup_codes,
    )


@router.get("/me", response_model=UserMeResponse)
async def get_current_user_info(
    current_user: CurrentUser,
) -> UserMeResponse:
    """
    Get the current authenticated user's information.

    Includes permissions based on the user's role.
    """
    permissions = {
        "can_manage_users": current_user.can_manage_users,
        "can_create_resources": current_user.can_create_resources,
        "is_admin": current_user.is_admin,
        "is_member": current_user.is_member,
        "is_viewer": current_user.is_viewer,
    }

    return UserMeResponse(
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.name,
        role=current_user.role,
        is_active=current_user.is_active,
        last_login_at=current_user.last_login_at,
        created_at=current_user.created_at,
        tenant_id=str(current_user.tenant_id),
        permissions=permissions,
        totp_enabled=current_user.totp_enabled,
    )


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    """
    Update the current user's profile.

    Users can only update their own name and email, not their role.
    """
    # Users cannot change their own role
    update_kwargs = {}
    if user_data.name is not None:
        update_kwargs["name"] = user_data.name
    if user_data.email is not None:
        update_kwargs["email"] = user_data.email

    if not update_kwargs:
        return user_to_response(current_user)

    user = await update_user(session, current_user.id, **update_kwargs)
    await session.commit()

    return user_to_response(user)


@router.post("/me/password", status_code=204)
async def change_own_password(
    password_data: UserPasswordUpdate,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    Change the current user's password.

    Requires the current password for verification.
    """
    # Verify current password
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    await update_user_password(session, current_user.id, password_data.new_password)
    await session.commit()


@router.get("", response_model=UsersResponse)
async def list_all_users(
    admin: CurrentUserAdmin,
    include_inactive: bool = False,
    session: AsyncSession = Depends(get_session),
) -> UsersResponse:
    """
    List all users in the tenant.

    **Admin only.** Returns all users for the current tenant.
    """
    users = await list_users(session, admin.tenant_id, include_inactive=include_inactive)

    return UsersResponse(
        users=[user_to_response(u) for u in users],
        total=len(users),
    )


@router.post("", response_model=UserResponse, status_code=201)
async def create_new_user(
    user_data: UserCreate,
    admin: CurrentUserAdmin,
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    """
    Create a new user.

    **Admin only.** Creates a new user in the current tenant.
    """
    try:
        role = UserRole(user_data.role)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role: {user_data.role}. Must be 'admin', 'member', or 'viewer'",
        )

    try:
        user = await create_user(
            session=session,
            tenant_id=admin.tenant_id,
            email=user_data.email,
            password=user_data.password,
            name=user_data.name,
            role=role,
        )
        await session.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return user_to_response(user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    admin: CurrentUserAdmin,
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    """
    Get a specific user by ID.

    **Admin only.**
    """
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    user = await get_user_by_id(session, user_uuid)

    if not user or user.tenant_id != admin.tenant_id:
        raise HTTPException(status_code=404, detail="User not found")

    return user_to_response(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user_by_id(
    user_id: str,
    user_data: UserUpdate,
    admin: CurrentUserAdmin,
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    """
    Update a user.

    **Admin only.** Can update name, email, role, and is_active status.
    """
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    user = await get_user_by_id(session, user_uuid)

    if not user or user.tenant_id != admin.tenant_id:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent removing last admin
    if user_data.role and user_data.role != "admin" and user.is_admin:
        admin_count = await count_admins(session, admin.tenant_id)
        if admin_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot remove the last admin. Promote another user first.",
            )

    # Prevent deactivating last admin
    if user_data.is_active is False and user.is_admin:
        admin_count = await count_admins(session, admin.tenant_id)
        if admin_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot deactivate the last admin.",
            )

    update_kwargs = {}
    if user_data.name is not None:
        update_kwargs["name"] = user_data.name
    if user_data.email is not None:
        update_kwargs["email"] = user_data.email
    if user_data.role is not None:
        update_kwargs["role"] = user_data.role
    if user_data.is_active is not None:
        update_kwargs["is_active"] = user_data.is_active

    if update_kwargs:
        user = await update_user(session, user_uuid, **update_kwargs)
        await session.commit()

    return user_to_response(user)


@router.delete("/{user_id}", status_code=204)
async def delete_user_by_id(
    user_id: str,
    admin: CurrentUserAdmin,
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    Delete a user.

    **Admin only.** Permanently deletes the user account.
    """
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    user = await get_user_by_id(session, user_uuid)

    if not user or user.tenant_id != admin.tenant_id:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent deleting last admin
    if user.is_admin:
        admin_count = await count_admins(session, admin.tenant_id)
        if admin_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete the last admin.",
            )

    # Prevent self-deletion
    if user.id == admin.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete your own account.",
        )

    await delete_user(session, user_uuid)
    await session.commit()
