"""External notification service.

Reads `TenantNotificationConfig` and posts to Slack / PagerDuty when run
events fire. Designed to be invoked fire-and-forget from the executor on
RunStatus transitions, so failures here MUST NOT block run completion.

For v1 the email-digest path is a no-op stub — the column is persisted and
a follow-up will add a daily cron job in services/digest.py to drain a
Redis-backed digest queue.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge_server.db import get_session_context
from flowforge_server.db.models import Run, TenantNotificationConfig
from flowforge_server.logging import Loggers

# Single shared client. Created lazily so tests can monkeypatch httpx.
_http_client: httpx.AsyncClient | None = None


def _client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=10.0)
    return _http_client


async def _load_config(
    session: AsyncSession, tenant_id: uuid.UUID
) -> TenantNotificationConfig | None:
    result = await session.execute(
        select(TenantNotificationConfig).where(
            TenantNotificationConfig.tenant_id == tenant_id
        )
    )
    return result.scalar_one_or_none()


async def _post_slack(webhook_url: str, *, channel: str | None, text: str, blocks: list[dict[str, Any]] | None = None) -> bool:
    """Post a message to a Slack incoming webhook. Returns success."""
    log = Loggers.api()
    payload: dict[str, Any] = {"text": text}
    if channel:
        payload["channel"] = channel
    if blocks:
        payload["blocks"] = blocks
    try:
        resp = await _client().post(webhook_url, json=payload)
        if resp.status_code >= 400:
            log.warning("notifier_slack_post_failed", status=resp.status_code, body=resp.text[:200])
            return False
        return True
    except Exception as e:  # network error, DNS failure, etc.
        log.warning("notifier_slack_post_error", error=str(e))
        return False


async def _post_pagerduty(integration_key: str, *, summary: str, severity: str, source: str, custom_details: dict[str, Any]) -> bool:
    """Trigger a PagerDuty incident via the Events API v2. Returns success."""
    log = Loggers.api()
    url = "https://events.pagerduty.com/v2/enqueue"
    payload = {
        "routing_key": integration_key,
        "event_action": "trigger",
        "payload": {
            "summary": summary,
            "severity": severity,  # one of: critical, error, warning, info
            "source": source,
            "custom_details": custom_details,
        },
    }
    try:
        resp = await _client().post(url, json=payload)
        if resp.status_code >= 400:
            log.warning("notifier_pagerduty_post_failed", status=resp.status_code, body=resp.text[:200])
            return False
        return True
    except Exception as e:
        log.warning("notifier_pagerduty_post_error", error=str(e))
        return False


def _format_run_failed_text(run: Run, function_name: str | None) -> str:
    fn_label = function_name or str(run.function_id)
    err = run.error or {}
    err_msg = err.get("message") if isinstance(err, dict) else str(err)
    return (
        f":rotating_light: FlowForge run *{run.id}* failed\n"
        f"Function: `{fn_label}`\n"
        f"Error: {err_msg or 'unknown'}"
    )


async def notify_run_failed(run_id: uuid.UUID | str) -> None:
    """Notify configured channels that a Run has reached a terminal failure.

    Fire-and-forget — must not raise. Looks up the run + function fresh so
    the caller doesn't have to keep a session open.
    """
    log = Loggers.api()
    try:
        run_uuid = uuid.UUID(str(run_id))
        async with get_session_context() as session:
            run_row = await session.execute(select(Run).where(Run.id == run_uuid))
            run = run_row.scalar_one_or_none()
            if not run:
                return

            cfg = await _load_config(session, run.tenant_id)
            if cfg is None or not cfg.notify_on_run_failed:
                return

            # Best-effort load function name
            function_name: str | None = None
            try:
                from flowforge_server.db.models import Function

                fn_row = await session.execute(
                    select(Function).where(Function.id == run.function_id)
                )
                fn = fn_row.scalar_one_or_none()
                function_name = fn.function_id if fn else None
            except Exception:  # pragma: no cover — purely cosmetic
                pass

            text = _format_run_failed_text(run, function_name)

            jobs: list[asyncio.Task[bool]] = []
            if cfg.slack_webhook_url:
                jobs.append(
                    asyncio.create_task(
                        _post_slack(
                            cfg.slack_webhook_url,
                            channel=cfg.slack_channel,
                            text=text,
                        )
                    )
                )
            if cfg.pagerduty_enabled and cfg.pagerduty_integration_key:
                err = run.error or {}
                err_msg = err.get("message") if isinstance(err, dict) else None
                jobs.append(
                    asyncio.create_task(
                        _post_pagerduty(
                            cfg.pagerduty_integration_key,
                            summary=f"FlowForge run failed: {function_name or run.function_id}",
                            severity="error",
                            source=str(run.tenant_id),
                            custom_details={
                                "run_id": str(run.id),
                                "function_id": str(run.function_id),
                                "error": err_msg,
                            },
                        )
                    )
                )
            if jobs:
                await asyncio.gather(*jobs, return_exceptions=True)
    except Exception as e:
        log.warning("notifier_run_failed_dispatch_error", error=str(e))


async def send_test(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    channel: str,
) -> tuple[bool, str]:
    """Fire a test message on a single channel. Used by the test endpoint."""
    cfg = await _load_config(session, tenant_id)
    if cfg is None:
        return False, "Notifications are not configured for this workspace."

    if channel == "slack":
        if not cfg.slack_webhook_url:
            return False, "Slack webhook URL is not set."
        ok = await _post_slack(
            cfg.slack_webhook_url,
            channel=cfg.slack_channel,
            text=":wave: Test notification from FlowForge — Slack integration is wired up.",
        )
        return ok, ("Sent." if ok else "Slack rejected the request — check the webhook URL.")

    if channel == "pagerduty":
        if not cfg.pagerduty_enabled:
            return False, "PagerDuty notifications are disabled."
        if not cfg.pagerduty_integration_key:
            return False, "PagerDuty integration key is not set."
        ok = await _post_pagerduty(
            cfg.pagerduty_integration_key,
            summary="FlowForge test notification",
            severity="info",
            source=str(tenant_id),
            custom_details={"test": True},
        )
        return ok, ("Sent." if ok else "PagerDuty rejected the request — check the integration key.")

    return False, f"Unknown channel: {channel}"
