"""Add deleted_at column to functions for soft-delete support."""

from sqlalchemy import text

MIGRATION_ID = "add_function_soft_delete"
MIGRATION_DATE = "2026-04-19"
DESCRIPTION = "Add deleted_at timestamp to functions for soft-delete"


ADD_DELETED_AT_COLUMN_SQL = """
    ALTER TABLE functions
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
"""

CREATE_DELETED_AT_INDEX_SQL = """
    CREATE INDEX IF NOT EXISTS ix_functions_deleted_at
    ON functions (deleted_at);
"""

DROP_DELETED_AT_INDEX_SQL = """
    DROP INDEX IF EXISTS ix_functions_deleted_at;
"""

DROP_DELETED_AT_COLUMN_SQL = """
    ALTER TABLE functions
    DROP COLUMN IF EXISTS deleted_at;
"""


async def upgrade(engine) -> None:
    """Entry point used by the migration runner in server/db/migrations.py."""
    async with engine.begin() as conn:
        await conn.execute(text(ADD_DELETED_AT_COLUMN_SQL))
        await conn.execute(text(CREATE_DELETED_AT_INDEX_SQL))


async def downgrade(engine) -> None:
    """Rollback entry point used by the migration runner."""
    async with engine.begin() as conn:
        await conn.execute(text(DROP_DELETED_AT_INDEX_SQL))
        await conn.execute(text(DROP_DELETED_AT_COLUMN_SQL))


async def up(session) -> None:
    """Apply migration (standalone/session variant kept for parity with peers)."""
    await session.execute(text(ADD_DELETED_AT_COLUMN_SQL))
    await session.execute(text(CREATE_DELETED_AT_INDEX_SQL))
    await session.commit()


async def down(session) -> None:
    """Rollback migration (session variant)."""
    await session.execute(text(DROP_DELETED_AT_INDEX_SQL))
    await session.execute(text(DROP_DELETED_AT_COLUMN_SQL))
    await session.commit()
