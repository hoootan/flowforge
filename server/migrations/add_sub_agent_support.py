"""Add sub-agent support: parent_run_id on runs and SUB_AGENT step type."""


# Migration metadata
MIGRATION_ID = "add_sub_agent_support"
MIGRATION_DATE = "2026-03-07"
DESCRIPTION = "Add parent_run_id to runs table and SUB_AGENT to step type enum"


async def up(session) -> None:
    """Apply migration."""
    # Add parent_run_id column to runs table
    await session.execute(
        """
        ALTER TABLE runs
        ADD COLUMN IF NOT EXISTS parent_run_id UUID
        REFERENCES runs(id) ON DELETE SET NULL;
        """
    )

    # Add index for parent_run_id
    await session.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_runs_parent_run_id
        ON runs(parent_run_id);
        """
    )

    await session.commit()


async def down(session) -> None:
    """Rollback migration."""
    await session.execute(
        """
        DROP INDEX IF EXISTS ix_runs_parent_run_id;
        """
    )

    await session.execute(
        """
        ALTER TABLE runs
        DROP COLUMN IF EXISTS parent_run_id;
        """
    )

    await session.commit()
