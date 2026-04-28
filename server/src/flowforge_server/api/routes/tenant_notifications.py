"""Workspace notification settings (Slack / PagerDuty / email digest).

Backed by the `tenant_notification_config` table; consumed by
services/notifier.py at run failure transitions.
"""

from datetime import UTC, datetime
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
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
from flowforge_server.services.network_utils import validate_webhook_url

# Slack incoming-webhook URLs are always served from this host. Pinning here
# is much tighter than generic SSRF protection and matches Slack's docs.
SLACK_WEBHOOK_HOST = "hooks.slack.com"

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


def _validate_slack_webhook(url: str | None) -> None:
    """Reject Slack webhook URLs that aren't safe to POST to.

    Two layers:
    1. ``validate_webhook_url`` (services/network_utils.py) blocks non-http(s)
       schemes, private IPs, and DNS-rebinding attacks.
    2. We additionally require the host to be ``hooks.slack.com`` — Slack's
       canonical incoming-webhook host. This is much tighter than generic
       SSRF protection.

    A None / empty value is treated as "clearing the setting" — no validation.
    """
    if not url:
        return
    try:
        validate_webhook_url(url)
    except Exception as exc:  # ValueError, ssrf rejection, etc.
        raise HTTPException(status_code=400, detail=f"Invalid Slack webhook URL: {exc}") from exc

    host = (urlparse(url).hostname or "").lower()
    if host != SLACK_WEBHOOK_HOST:
        raise HTTPException(
            status_code=400,
            detail=f"Slack webhook URL must be on {SLACK_WEBHOOK_HOST}.",
        )


@router.get("", response_model=NotificationSettings)
async def get_settings(
    tenant: TenantWithDevFallback,
    _admin: CurrentUserAdmin,
    session: AsyncSession = Depends(get_session),
) -> NotificationSettings:
    """Return notification settings for the workspace (defaults if unset).

    Admin-only — the response includes secret values (Slack webhook URL,
    PagerDuty integration key) so non-admin members must not see them.
    """
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
    Slack webhook URLs are validated for SSRF safety + host pinning.
    """
    patch = update_data.model_dump(exclude_unset=True)
    if "slack_webhook_url" in patch:
        _validate_slack_webhook(patch["slack_webhook_url"])

    result = await session.execute(
        select(TenantNotificationConfig).where(
            TenantNotificationConfig.tenant_id == tenant.id
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = TenantNotificationConfig(tenant_id=tenant.id)
        session.add(row)

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
