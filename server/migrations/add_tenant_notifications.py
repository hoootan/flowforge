"""Per-tenant notification config (Slack / PagerDuty / email digest).

Workspace-level settings that drive `services/notifier.py`. The webhook URL
and PagerDuty integration key live here directly (encrypted at rest by the
column-level encryption used elsewhere is *not* applied here for v1 — these
are workspace operational secrets, not user secrets, and they're admin-only
to read/write; if we later need encryption, swap to a Credential FK).
"""

from sqlalchemy import text

MIGRATION_ID = "add_tenant_notifications"
MIGRATION_DATE = "2026-04-28"
DESCRIPTION = "Per-tenant notification config table for Slack / PagerDuty / email digest"


CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS tenant_notification_config (
        tenant_id UUID PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,

        slack_channel TEXT,
        slack_webhook_url TEXT,

        pagerduty_enabled BOOLEAN NOT NULL DEFAULT FALSE,
        pagerduty_integration_key TEXT,

        email_digest_enabled BOOLEAN NOT NULL DEFAULT FALSE,

        notify_on_run_failed BOOLEAN NOT NULL DEFAULT TRUE,
        notify_on_run_timeout BOOLEAN NOT NULL DEFAULT TRUE,

        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
"""

DROP_TABLE_SQL = """
    DROP TABLE IF EXISTS tenant_notification_config;
"""


async def upgrade(engine) -> None:
    """Entry point used by the migration runner in server/db/migrations.py."""
    async with engine.begin() as conn:
        await conn.execute(text(CREATE_TABLE_SQL))


async def downgrade(engine) -> None:
    """Rollback entry point used by the migration runner."""
    async with engine.begin() as conn:
        await conn.execute(text(DROP_TABLE_SQL))


async def up(session) -> None:
    """Apply migration (session variant)."""
    await session.execute(text(CREATE_TABLE_SQL))
    await session.commit()


async def down(session) -> None:
    """Rollback migration (session variant)."""
    await session.execute(text(DROP_TABLE_SQL))
    await session.commit()
