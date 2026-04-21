"""Partial index on steps.scheduled_at for SLEEPING rows only.

The runner's `_process_scheduled_runs_once` scan (server/src/flowforge_server/
services/runner.py) selects steps with `status='sleeping' AND scheduled_at<=now`.
Without a partial index it uses the general `ix_steps_scheduled_at` single-column
index, which over time grows to include every completed sleep (scheduled_at is
not cleared when we mark the step COMPLETED). A partial index keeps only active
sleeps in-tree and makes the scan O(active sleeps) regardless of history.

Built with CREATE INDEX CONCURRENTLY so we do not take an ACCESS EXCLUSIVE lock
on `steps` during the index build — important for prod rollouts on a sizable
history. CONCURRENTLY cannot run inside a transaction, so this migration opens
its own AUTOCOMMIT connection rather than using `engine.begin()`. See the
migration runner in server/src/flowforge_server/db/migrations.py for the
invocation path.
"""

from sqlalchemy import text

MIGRATION_ID = "add_sleep_wake_partial_index"
MIGRATION_DATE = "2026-04-21"
DESCRIPTION = "Partial index on steps.scheduled_at WHERE status='sleeping'"


CREATE_INDEX_SQL = """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_steps_sleeping_due
    ON steps (scheduled_at)
    WHERE status = 'sleeping';
"""

DROP_INDEX_SQL = """
    DROP INDEX CONCURRENTLY IF EXISTS ix_steps_sleeping_due;
"""


async def upgrade(engine) -> None:
    """Entry point used by the migration runner in
    server/src/flowforge_server/db/migrations.py.

    CREATE INDEX CONCURRENTLY must run outside a transaction, so we open a
    raw connection with AUTOCOMMIT isolation rather than ``engine.begin()``.
    """
    async with engine.connect() as conn:
        conn = await conn.execution_options(isolation_level="AUTOCOMMIT")
        await conn.execute(text(CREATE_INDEX_SQL))


async def downgrade(engine) -> None:
    """Rollback entry point used by the migration runner.

    DROP INDEX CONCURRENTLY also requires autocommit.
    """
    async with engine.connect() as conn:
        conn = await conn.execution_options(isolation_level="AUTOCOMMIT")
        await conn.execute(text(DROP_INDEX_SQL))


async def up(session) -> None:
    """Apply migration (standalone/session variant kept for parity with peers).

    Commits any open transaction on the session first so CONCURRENTLY can run
    outside a transaction block on an AUTOCOMMIT connection.
    """
    await session.commit()
    conn = await session.connection(
        execution_options={"isolation_level": "AUTOCOMMIT"}
    )
    await conn.execute(text(CREATE_INDEX_SQL))


async def down(session) -> None:
    """Rollback migration (session variant)."""
    await session.commit()
    conn = await session.connection(
        execution_options={"isolation_level": "AUTOCOMMIT"}
    )
    await conn.execute(text(DROP_INDEX_SQL))
