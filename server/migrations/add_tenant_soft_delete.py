"""Soft-delete column on tenants for the Settings → Danger zone flow.

Setting `tenants.deleted_at` makes the workspace invisible to all routes
(via the get_current_tenant dependency filter) without erasing data, so a
mistaken delete is recoverable for the retention window.
"""

from sqlalchemy import text

MIGRATION_ID = "add_tenant_soft_delete"
MIGRATION_DATE = "2026-04-28"
DESCRIPTION = "Soft-delete column on tenants for danger-zone delete flow"


ADD_COLUMN_SQL = """
    ALTER TABLE tenants
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
"""

CREATE_INDEX_SQL = """
    CREATE INDEX IF NOT EXISTS ix_tenants_deleted_at
    ON tenants (deleted_at);
"""

DROP_INDEX_SQL = """
    DROP INDEX IF EXISTS ix_tenants_deleted_at;
"""

DROP_COLUMN_SQL = """
    ALTER TABLE tenants
    DROP COLUMN IF EXISTS deleted_at;
"""


async def upgrade(engine) -> None:
    """Entry point used by the migration runner in server/db/migrations.py."""
    async with engine.begin() as conn:
        await conn.execute(text(ADD_COLUMN_SQL))
        await conn.execute(text(CREATE_INDEX_SQL))


async def downgrade(engine) -> None:
    """Rollback entry point used by the migration runner."""
    async with engine.begin() as conn:
        await conn.execute(text(DROP_INDEX_SQL))
        await conn.execute(text(DROP_COLUMN_SQL))


async def up(session) -> None:
    await session.execute(text(ADD_COLUMN_SQL))
    await session.execute(text(CREATE_INDEX_SQL))
    await session.commit()


async def down(session) -> None:
    await session.execute(text(DROP_INDEX_SQL))
    await session.execute(text(DROP_COLUMN_SQL))
    await session.commit()
