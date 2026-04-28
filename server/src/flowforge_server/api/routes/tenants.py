"""Tenant/workspace settings endpoints.

Currently exposes the workspace-level concurrency & limits settings used by
the runner and executor. Additional sections (general, notifications, danger
zone) live in sibling routes or future migrations.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from flowforge_server.api.deps import CurrentUserAdmin, TenantWithDevFallback
from flowforge_server.api.schemas.tenant import (
    ConcurrencySettings,
    ConcurrencySettingsUpdate,
)
from flowforge_server.db import get_session
from flowforge_server.db.models import Tenant

router = APIRouter(prefix="/tenant", tags=["tenant"])


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
    # the JSONB write participates in the transaction.
    settings = dict(tenant.settings or {})
    settings[CONCURRENCY_KEY] = merged.model_dump()

    await session.execute(
        update(Tenant).where(Tenant.id == tenant.id).values(settings=settings)
    )
    # Mirror the new value onto the in-memory tenant the dep handed us.
    tenant.settings = settings
    flag_modified(tenant, "settings")
    await session.commit()

    return merged
