"""Add composite index on steps(status, wait_event_name) for wait-for-event resolution."""


# Migration metadata
MIGRATION_ID = "add_step_wait_event_index"
MIGRATION_DATE = "2026-04-16"
DESCRIPTION = "Add index for efficient waiting step lookups by event name"


async def up(session) -> None:
    """Apply migration."""
    await session.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_step_status_wait_event
        ON steps (status, wait_event_name);
        """
    )
    await session.commit()
