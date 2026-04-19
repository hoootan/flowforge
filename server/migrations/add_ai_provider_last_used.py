"""
Migration: Add last_used_at column to ai_providers table.

Tracks the most recent time a provider's credential was used by the
AI service. Surfaced in the dashboard as "Last used N ago".
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def upgrade(engine: AsyncEngine) -> None:
    """Apply the migration."""
    async with engine.begin() as conn:
        await conn.execute(text("""
            ALTER TABLE ai_providers
            ADD COLUMN IF NOT EXISTS last_used_at TIMESTAMP WITH TIME ZONE NULL
        """))


async def downgrade(engine: AsyncEngine) -> None:
    """Revert the migration."""
    async with engine.begin() as conn:
        await conn.execute(text("""
            ALTER TABLE ai_providers
            DROP COLUMN IF EXISTS last_used_at
        """))


if __name__ == "__main__":
    import asyncio

    from flowforge_server.db import get_engine

    async def main() -> None:
        engine = get_engine()
        print("Running migration: add_ai_provider_last_used")
        await upgrade(engine)
        print("Migration completed successfully")

    asyncio.run(main())
