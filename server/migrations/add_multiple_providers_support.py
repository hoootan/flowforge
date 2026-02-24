"""
Migration: Allow multiple AI providers per type

This migration:
1. Drops the unique constraint (tenant_id, provider_name) so tenants
   can have multiple providers of the same type (e.g., two Anthropic keys).

Created: 2026-02-24
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def upgrade(engine: AsyncEngine) -> None:
    """Apply the migration."""
    async with engine.begin() as conn:
        # Drop the unique constraint that limits one provider per type per tenant
        await conn.execute(text("""
            ALTER TABLE ai_providers
            DROP CONSTRAINT IF EXISTS uq_ai_provider_tenant_name
        """))


async def downgrade(engine: AsyncEngine) -> None:
    """Revert the migration."""
    async with engine.begin() as conn:
        await conn.execute(text("""
            ALTER TABLE ai_providers
            ADD CONSTRAINT uq_ai_provider_tenant_name
            UNIQUE (tenant_id, provider_name)
        """))


if __name__ == "__main__":
    """Run migration manually."""
    import asyncio
    from flowforge_server.db import get_engine

    async def main():
        engine = get_engine()
        print("Running migration: add_multiple_providers_support")
        await upgrade(engine)
        print("Migration completed successfully")

    asyncio.run(main())
