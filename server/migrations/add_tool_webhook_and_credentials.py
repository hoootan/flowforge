"""
Migration: Add credentials table and webhook columns to tools

This migration adds:
1. A new credentials table for encrypted service credential storage
2. New columns on tools table: tool_type, webhook_url, webhook_method, webhook_headers

Created: 2026-03-06
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def upgrade(engine: AsyncEngine) -> None:
    """Apply the migration."""
    async with engine.begin() as conn:
        # ── credentials table ──
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS credentials (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                credential_type VARCHAR(20) NOT NULL DEFAULT 'api_key',
                encrypted_value TEXT NOT NULL,
                value_prefix VARCHAR(20) NOT NULL,
                description TEXT,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                CONSTRAINT uq_credential_tenant_name UNIQUE(tenant_id, name)
            )
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_credentials_tenant_id
            ON credentials(tenant_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_credentials_name
            ON credentials(name)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_credential_tenant_active
            ON credentials(tenant_id, is_active)
        """))

        # ── tool webhook columns ──
        await conn.execute(text("""
            ALTER TABLE tools
            ADD COLUMN IF NOT EXISTS tool_type VARCHAR(20) NOT NULL DEFAULT 'custom'
        """))
        await conn.execute(text("""
            ALTER TABLE tools
            ADD COLUMN IF NOT EXISTS webhook_url TEXT
        """))
        await conn.execute(text("""
            ALTER TABLE tools
            ADD COLUMN IF NOT EXISTS webhook_method VARCHAR(10) NOT NULL DEFAULT 'POST'
        """))
        await conn.execute(text("""
            ALTER TABLE tools
            ADD COLUMN IF NOT EXISTS webhook_headers JSONB
        """))


async def downgrade(engine: AsyncEngine) -> None:
    """Revert the migration."""
    async with engine.begin() as conn:
        # Drop tool columns
        await conn.execute(text("ALTER TABLE tools DROP COLUMN IF EXISTS webhook_headers"))
        await conn.execute(text("ALTER TABLE tools DROP COLUMN IF EXISTS webhook_method"))
        await conn.execute(text("ALTER TABLE tools DROP COLUMN IF EXISTS webhook_url"))
        await conn.execute(text("ALTER TABLE tools DROP COLUMN IF EXISTS tool_type"))

        # Drop credentials indexes
        await conn.execute(text("DROP INDEX IF EXISTS ix_credential_tenant_active"))
        await conn.execute(text("DROP INDEX IF EXISTS ix_credentials_name"))
        await conn.execute(text("DROP INDEX IF EXISTS ix_credentials_tenant_id"))

        # Drop credentials table
        await conn.execute(text("DROP TABLE IF EXISTS credentials"))


if __name__ == "__main__":
    """Run migration manually."""
    import asyncio

    from flowforge_server.db import get_engine

    async def main():
        engine = get_engine()
        print("Running migration: add_tool_webhook_and_credentials")
        await upgrade(engine)
        print("Migration completed successfully")

    asyncio.run(main())
