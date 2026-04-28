"""Tenant/workspace settings endpoints.

Currently exposes:
- workspace-level concurrency & limits settings (used by runner/executor)
- danger zone actions: pause-all, transfer-ownership, soft-delete

Notifications live in sibling route `tenant_notifications.py`.
"""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from flowforge_server.api.deps import CurrentUserAdmin, TenantWithDevFallback
from flowforge_server.api.schemas.tenant import (
    ConcurrencySettings,
    ConcurrencySettingsUpdate,
)
from flowforge_server.db import get_session
from flowforge_server.db.models import Function, Tenant, User, UserRole

router = APIRouter(prefix="/tenant", tags=["tenant"])


class TenantInfo(BaseModel):
    """Minimal workspace metadata used by the dashboard."""

    id: str
    name: str
    slug: str
    deleted_at: datetime | None = None


@router.get("", response_model=TenantInfo)
async def get_tenant(tenant: TenantWithDevFallback) -> TenantInfo:
    """Return current workspace identity. Available to any authenticated caller."""
    return TenantInfo(
        id=str(tenant.id),
        name=tenant.name,
        slug=tenant.slug,
        deleted_at=getattr(tenant, "deleted_at", None),
    )


# Key inside Tenant.settings JSONB where concurrency config lives. Keep this
# constant in sync with consumers in services/runner.py and queue/fair_queue.py.
CONCURRENCY_KEY = "concurrency"


def _read_concurrency(tenant: Tenant) -> ConcurrencySettings:
    """Load (or default-fill) the concurrency block from a Tenant row."""
    raw = (tenant.settings or {}).get(CONCURRENCY_KEY) or {}
    # Pydantic validates and fills defaults for missing fields.
    return ConcurrencySettings(**{k: v for k, v in raw.items() if v is not None})


@router.get("/concurrency", response_model=ConcurrencySettings)
async def get_concurrency(
    tenant: TenantWithDevFallback,
) -> ConcurrencySettings:
    """Return the workspace-level concurrency and limits settings."""
    return _read_concurrency(tenant)


@router.patch("/concurrency", response_model=ConcurrencySettings)
async def update_concurrency(
    update_data: ConcurrencySettingsUpdate,
    tenant: TenantWithDevFallback,
    _admin: CurrentUserAdmin,
    session: AsyncSession = Depends(get_session),
) -> ConcurrencySettings:
    """Update workspace-level concurrency settings. Admin-only."""
    current = _read_concurrency(tenant)

    # Apply only the fields the caller actually provided
    patch = update_data.model_dump(exclude_unset=True)
    merged = current.model_copy(update=patch)

    # Persist back to the tenant row. We re-fetch through the request session so
    # the JSONB write participates in the transaction. ORM-only path —
    # mutating the attached instance and flagging the JSONB key as modified
    # is the canonical SQLAlchemy pattern; an explicit `update(...)` here
    # would fire a second UPDATE on commit.
    settings = dict(tenant.settings or {})
    settings[CONCURRENCY_KEY] = merged.model_dump()

    tenant.settings = settings
    flag_modified(tenant, "settings")
    await session.commit()

    return merged


# ---------------------------------------------------------------------------
# Danger zone
# ---------------------------------------------------------------------------


class PauseAllResponse(BaseModel):
    """Result of pausing every function in the workspace."""

    paused_count: int


class TransferOwnershipRequest(BaseModel):
    """Body for transfer-ownership: who becomes the new admin owner."""

    user_id: str = Field(description="UUID of the user that should become admin.")


class TransferOwnershipResponse(BaseModel):
    new_owner_id: str
    new_owner_email: str


class DeleteWorkspaceRequest(BaseModel):
    """Body for delete-workspace. Caller must echo the slug to confirm."""

    confirm_slug: str = Field(
        description="The workspace slug, retyped to confirm intent. Mismatch returns 400.",
    )


class DeleteWorkspaceResponse(BaseModel):
    deleted_at: datetime


@router.post("/pause-all", response_model=PauseAllResponse)
async def pause_all_functions(
    tenant: TenantWithDevFallback,
    _admin: CurrentUserAdmin,
    session: AsyncSession = Depends(get_session),
) -> PauseAllResponse:
    """Set is_active=false on every Function in the workspace.

    Admin-only. Idempotent — subsequent calls return paused_count == 0 once
    everything is already paused. New events still create runs that match
    inactive functions; the runner skips them via Function.is_active filter.
    """
    result = await session.execute(
        update(Function)
        .where(
            Function.tenant_id == tenant.id,
            Function.is_active.is_(True),
        )
        .values(is_active=False)
        .execution_options(synchronize_session=False)
    )
    await session.commit()
    paused = result.rowcount or 0
    return PauseAllResponse(paused_count=paused)


@router.post("/transfer-ownership", response_model=TransferOwnershipResponse)
async def transfer_ownership(
    body: TransferOwnershipRequest,
    tenant: TenantWithDevFallback,
    admin: CurrentUserAdmin,
    session: AsyncSession = Depends(get_session),
) -> TransferOwnershipResponse:
    """Promote the target user to admin and demote the calling admin to member.

    Admin-only. Both users must already exist in the same tenant.
    """
    try:
        target_id = uuid.UUID(body.user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id.")

    if target_id == admin.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot transfer ownership to yourself.",
        )

    target_row = await session.execute(
        select(User).where(
            User.id == target_id,
            User.tenant_id == tenant.id,
        )
    )
    target = target_row.scalar_one_or_none()
    if target is None:
        raise HTTPException(
            status_code=404,
            detail="Target user not found in this workspace.",
        )

    target.role = UserRole.ADMIN.value
    admin.role = UserRole.MEMBER.value

    await session.commit()
    return TransferOwnershipResponse(
        new_owner_id=str(target.id),
        new_owner_email=target.email,
    )


@router.delete("", response_model=DeleteWorkspaceResponse)
async def delete_workspace(
    body: DeleteWorkspaceRequest,
    tenant: TenantWithDevFallback,
    _admin: CurrentUserAdmin,
    session: AsyncSession = Depends(get_session),
) -> DeleteWorkspaceResponse:
    """Soft-delete the workspace by stamping `deleted_at`.

    Admin-only. The caller must echo the workspace slug to confirm intent.
    Subsequent auth attempts on this tenant return 410 Gone (see
    api/deps.py::_bounce_if_deleted). Hard delete is left for a future
    background job; this is reversible until then.
    """
    if body.confirm_slug.strip() != (tenant.slug or "").strip():
        raise HTTPException(
            status_code=400,
            detail="confirm_slug does not match the workspace slug.",
        )

    # ORM-only mutation; the attached instance flushes one UPDATE on commit.
    now = datetime.now(UTC)
    tenant.deleted_at = now
    await session.commit()
    return DeleteWorkspaceResponse(deleted_at=now)
