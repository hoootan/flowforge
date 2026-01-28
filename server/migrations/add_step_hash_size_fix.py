"""
Migration: Fix step_hash column size

The step_hash column was VARCHAR(32) but needs to accommodate longer
identifiers like 'agent:9bbefd19-2931-4187-8cde-bfe0858b2528:1'.

Created: 2026-01-24
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def upgrade(engine: AsyncEngine) -> None:
    """Apply the migration."""
    async with engine.begin() as conn:
        # Increase step_hash column size
        await conn.execute(text("""
            ALTER TABLE steps
            ALTER COLUMN step_hash TYPE VARCHAR(255)
        """))


async def downgrade(engine: AsyncEngine) -> None:
    """Revert the migration."""
    async with engine.begin() as conn:
        # Note: This may fail if there are values longer than 32 chars
        await conn.execute(text("""
            ALTER TABLE steps
            ALTER COLUMN step_hash TYPE VARCHAR(32)
        """))
