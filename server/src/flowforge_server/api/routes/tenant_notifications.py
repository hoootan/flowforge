"""Workspace notification settings (Slack / PagerDuty / email digest).

Backed by the `tenant_notification_config` table; consumed by
services/notifier.py at run failure transitions.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge_server.api.deps import CurrentUserAdmin, TenantWithDevFallback
from flowforge_server.api.schemas.notifications_settings import (
    NotificationSettings,
    NotificationSettingsUpdate,
    NotificationTestRequest,
    NotificationTestResponse,
)
from flowforge_server.db import get_session
from flowforge_server.db.models import TenantNotificationConfig
from flowforge_server.services import notifier as notifier_service

router = APIRouter(prefix="/tenant/notifications", tags=["tenant"])


def _row_to_response(row: TenantNotificationConfig | None) -> NotificationSettings:
    """Map DB row → API response, falling back to defaults when no row exists."""
    if row is None:
        return NotificationSettings()
    return NotificationSettings(
        slack_channel=row.slack_channel,
        slack_webhook_url=row.slack_webhook_url,
        pagerduty_enabled=row.pagerduty_enabled,
        pagerduty_integration_key=row.pagerduty_integration_key,
        email_digest_enabled=row.email_digest_enabled,
        notify_on_run_failed=row.notify_on_run_failed,
        notify_on_run_timeout=row.notify_on_run_timeout,
    )


@router.get("", response_model=NotificationSettings)
async def get_settings(
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> NotificationSettings:
    """Return notification settings for the workspace (defaults if unset)."""
    result = await session.execute(
        select(TenantNotificationConfig).where(
            TenantNotificationConfig.tenant_id == tenant.id
        )
    )
    return _row_to_response(result.scalar_one_or_none())


@router.patch("", response_model=NotificationSettings)
async def update_settings(
    update_data: NotificationSettingsUpdate,
    tenant: TenantWithDevFallback,
    _admin: CurrentUserAdmin,
    session: AsyncSession = Depends(get_session),
) -> NotificationSettings:
    """Patch the workspace notification settings. Admin-only.

    Upserts the row — first call for a tenant materializes the config.
    """
    result = await session.execute(
        select(TenantNotificationConfig).where(
            TenantNotificationConfig.tenant_id == tenant.id
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = TenantNotificationConfig(tenant_id=tenant.id)
        session.add(row)

    patch = update_data.model_dump(exclude_unset=True)
    for k, v in patch.items():
        setattr(row, k, v)
    row.updated_at = datetime.now(UTC)

    await session.commit()
    await session.refresh(row)
    return _row_to_response(row)


@router.post("/test", response_model=NotificationTestResponse)
async def test_notification(
    body: NotificationTestRequest,
    tenant: TenantWithDevFallback,
    _admin: CurrentUserAdmin,
    session: AsyncSession = Depends(get_session),
) -> NotificationTestResponse:
    """Fire a test message on the requested channel."""
    ok, message = await notifier_service.send_test(
        session, tenant.id, channel=body.channel
    )
    return NotificationTestResponse(ok=ok, channel=body.channel, message=message)
