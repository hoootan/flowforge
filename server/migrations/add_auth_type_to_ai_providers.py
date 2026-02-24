"""
Migration: Add auth_type column to ai_providers table

This migration adds:
1. An auth_type column to support both API key and OAuth token authentication
2. Default value of "api_key" for backward compatibility

Created: 2026-02-24
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def upgrade(engine: AsyncEngine) -> None:
    """Apply the migration."""
    async with engine.begin() as conn:
        # Add auth_type column with default "api_key" for existing rows
        await conn.execute(text("""
            ALTER TABLE ai_providers
            ADD COLUMN IF NOT EXISTS auth_type VARCHAR(20) NOT NULL DEFAULT 'api_key'
        """))


async def downgrade(engine: AsyncEngine) -> None:
    """Revert the migration."""
    async with engine.begin() as conn:
        await conn.execute(text("""
            ALTER TABLE ai_providers
            DROP COLUMN IF EXISTS auth_type
        """))


if __name__ == "__main__":
    """Run migration manually."""
    import asyncio
    from flowforge_server.db import get_engine

    async def main():
        engine = get_engine()
        print("Running migration: add_auth_type_to_ai_providers")
        await upgrade(engine)
        print("Migration completed successfully")

    asyncio.run(main())
