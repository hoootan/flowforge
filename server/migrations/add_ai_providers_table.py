"""
Migration: Add ai_providers table

This migration adds:
1. A new ai_providers table for secure per-tenant AI credential storage
2. Encrypted API key storage using Fernet encryption
3. Appropriate indexes and constraints for performance and data integrity

Created: 2026-01-31
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def upgrade(engine: AsyncEngine) -> None:
    """Apply the migration."""
    async with engine.begin() as conn:
        # Create ai_providers table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ai_providers (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                provider_name VARCHAR(50) NOT NULL,
                display_name VARCHAR(255) NOT NULL,
                api_key_encrypted TEXT NOT NULL,
                api_key_prefix VARCHAR(20) NOT NULL,
                base_url TEXT,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                is_default BOOLEAN NOT NULL DEFAULT FALSE,
                config JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                CONSTRAINT uq_ai_provider_tenant_name UNIQUE(tenant_id, provider_name)
            )
        """))

        # Create indexes
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_ai_providers_tenant_id
            ON ai_providers(tenant_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_ai_providers_provider_name
            ON ai_providers(provider_name)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_ai_provider_tenant_default
            ON ai_providers(tenant_id, is_default)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_ai_provider_tenant_active
            ON ai_providers(tenant_id, is_active)
        """))


async def downgrade(engine: AsyncEngine) -> None:
    """Revert the migration."""
    async with engine.begin() as conn:
        # Drop indexes
        await conn.execute(text("DROP INDEX IF EXISTS ix_ai_provider_tenant_active"))
        await conn.execute(text("DROP INDEX IF EXISTS ix_ai_provider_tenant_default"))
        await conn.execute(text("DROP INDEX IF EXISTS ix_ai_providers_provider_name"))
        await conn.execute(text("DROP INDEX IF EXISTS ix_ai_providers_tenant_id"))

        # Drop table
        await conn.execute(text("DROP TABLE IF EXISTS ai_providers"))


if __name__ == "__main__":
    """Run migration manually."""
    import asyncio

    from flowforge_server.db import get_engine

    async def main():
        engine = get_engine()
        print("Running migration: add_ai_providers_table")
        await upgrade(engine)
        print("Migration completed successfully")

    asyncio.run(main())
