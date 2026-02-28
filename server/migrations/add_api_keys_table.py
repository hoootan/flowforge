"""
Migration: Add API keys table

This migration adds:
1. A new api_keys table for enhanced API key management
2. Multiple keys per tenant with scopes and expiration
3. Appropriate indexes for performance

Created: 2026-01-28
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def upgrade(engine: AsyncEngine) -> None:
    """Apply the migration."""
    async with engine.begin() as conn:
        # Create api_keys table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                key_hash TEXT NOT NULL UNIQUE,
                key_prefix VARCHAR(20) NOT NULL,
                key_type VARCHAR(20) NOT NULL DEFAULT 'test',
                scopes TEXT[] NOT NULL DEFAULT '{}',
                expires_at TIMESTAMP WITH TIME ZONE,
                last_used_at TIMESTAMP WITH TIME ZONE,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                revoked_at TIMESTAMP WITH TIME ZONE,
                revoked_reason TEXT,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
        """))

        # Create indexes
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_api_keys_tenant_id ON api_keys(tenant_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_api_keys_key_prefix ON api_keys(key_prefix)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_api_keys_is_active ON api_keys(is_active)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_api_keys_key_type ON api_keys(key_type)
        """))


async def downgrade(engine: AsyncEngine) -> None:
    """Revert the migration."""
    async with engine.begin() as conn:
        # Drop indexes
        await conn.execute(text("DROP INDEX IF EXISTS idx_api_keys_key_type"))
        await conn.execute(text("DROP INDEX IF EXISTS idx_api_keys_is_active"))
        await conn.execute(text("DROP INDEX IF EXISTS idx_api_keys_key_prefix"))
        await conn.execute(text("DROP INDEX IF EXISTS idx_api_keys_key_hash"))
        await conn.execute(text("DROP INDEX IF EXISTS idx_api_keys_tenant_id"))

        # Drop table
        await conn.execute(text("DROP TABLE IF EXISTS api_keys"))


if __name__ == "__main__":
    """Run migration manually."""
    import asyncio

    from flowforge_server.db import get_engine

    async def main():
        engine = get_engine()
        print("Running migration: add_api_keys_table")
        await upgrade(engine)
        print("Migration completed successfully")

    asyncio.run(main())
