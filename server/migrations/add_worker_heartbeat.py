"""Add worker_last_seen field to functions table for worker health tracking."""


# Migration metadata
MIGRATION_ID = "add_worker_heartbeat"
MIGRATION_DATE = "2025-01-29"
DESCRIPTION = "Add worker_last_seen timestamp for worker health tracking"


async def up(session) -> None:
    """Apply migration."""
    await session.execute(
        """
        ALTER TABLE functions
        ADD COLUMN IF NOT EXISTS worker_last_seen TIMESTAMP;
        """
    )
    await session.commit()


async def down(session) -> None:
    """Rollback migration."""
    await session.execute(
        """
        ALTER TABLE functions
        DROP COLUMN IF EXISTS worker_last_seen;
        """
    )
    await session.commit()
