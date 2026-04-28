"""Partial UNIQUE index on runs(tenant_id, idempotency_key).

Defense-in-depth for the Phase 2 idempotency feature: when the workspace
flag `use_event_id_idempotency` is on, runner._create_run sets
Run.idempotency_key from the trigger event id. The runner now does an
optimistic query-then-insert with IntegrityError handling, but the
UNIQUE index closes the race window when two runners process a
redelivered event concurrently.

Partial because most rows still have idempotency_key=NULL (manually-set
keys are rare today); a partial index keeps NULL rows out of the index
and avoids the all-NULLs-collide issue that a plain UNIQUE would have
on Postgres (NULL != NULL is fine, but the index is also smaller).

Built with CREATE UNIQUE INDEX CONCURRENTLY so we do not take an
ACCESS EXCLUSIVE lock on `runs` during the index build. CONCURRENTLY
cannot run inside a transaction, so this migration uses an AUTOCOMMIT
connection. See migrations.py for the runner and
add_sleep_wake_partial_index.py for the same pattern.
"""

from sqlalchemy import text

MIGRATION_ID = "add_runs_idempotency_unique"
MIGRATION_DATE = "2026-04-28"
DESCRIPTION = "Partial UNIQUE index on runs(tenant_id, idempotency_key) WHERE idempotency_key IS NOT NULL"


CREATE_INDEX_SQL = """
    CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_runs_tenant_idempotency
    ON runs (tenant_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;
"""

DROP_INDEX_SQL = """
    DROP INDEX CONCURRENTLY IF EXISTS uq_runs_tenant_idempotency;
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
    """Rollback entry point used by the migration runner."""
    async with engine.connect() as conn:
        conn = await conn.execution_options(isolation_level="AUTOCOMMIT")
        await conn.execute(text(DROP_INDEX_SQL))
