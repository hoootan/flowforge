"""Add deleted_at column to functions for soft-delete support."""


MIGRATION_ID = "add_function_soft_delete"
MIGRATION_DATE = "2026-04-19"
DESCRIPTION = "Add deleted_at timestamp to functions for soft-delete"


async def up(session) -> None:
    """Apply migration."""
    await session.execute(
        """
        ALTER TABLE functions
        ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP;
        """
    )
    await session.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_functions_deleted_at
        ON functions (deleted_at);
        """
    )
    await session.commit()


async def down(session) -> None:
    """Rollback migration."""
    await session.execute(
        """
        DROP INDEX IF EXISTS ix_functions_deleted_at;
        """
    )
    await session.execute(
        """
        ALTER TABLE functions
        DROP COLUMN IF EXISTS deleted_at;
        """
    )
    await session.commit()
