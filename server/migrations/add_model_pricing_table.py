"""
Migration: Add model_pricing table

This migration adds:
1. A new model_pricing table for configurable AI model pricing
2. Support for both tenant-specific and global (NULL tenant_id) pricing
3. Unique constraint on (tenant_id, model_id) to prevent duplicates

Pricing resolution order:
1. Tenant-specific custom pricing (highest priority)
2. Global custom pricing (tenant_id is NULL)
3. Hardcoded defaults in DEFAULT_MODEL_CONFIGS
4. Fallback pricing for unknown models

Created: 2026-01-31
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def upgrade(engine: AsyncEngine) -> None:
    """Apply the migration."""
    async with engine.begin() as conn:
        # Create model_pricing table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS model_pricing (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
                model_id VARCHAR(255) NOT NULL,
                provider VARCHAR(64) NOT NULL,
                input_price_per_m DOUBLE PRECISION NOT NULL,
                output_price_per_m DOUBLE PRECISION NOT NULL,
                display_name VARCHAR(255),
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                CONSTRAINT uq_model_pricing_tenant_model UNIQUE(tenant_id, model_id)
            )
        """))

        # Create indexes
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_model_pricing_tenant_id
            ON model_pricing(tenant_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_model_pricing_model_id
            ON model_pricing(model_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_model_pricing_global
            ON model_pricing(model_id) WHERE tenant_id IS NULL
        """))


async def downgrade(engine: AsyncEngine) -> None:
    """Revert the migration."""
    async with engine.begin() as conn:
        # Drop indexes
        await conn.execute(text("DROP INDEX IF EXISTS ix_model_pricing_global"))
        await conn.execute(text("DROP INDEX IF EXISTS ix_model_pricing_model_id"))
        await conn.execute(text("DROP INDEX IF EXISTS ix_model_pricing_tenant_id"))

        # Drop table
        await conn.execute(text("DROP TABLE IF EXISTS model_pricing"))


if __name__ == "__main__":
    """Run migration manually."""
    import asyncio
    from flowforge_server.db import get_engine

    async def main():
        engine = get_engine()
        print("Running migration: add_model_pricing_table")
        await upgrade(engine)
        print("Migration completed successfully")

    asyncio.run(main())
