"""
Migration: Add audit_logs table

This migration adds the audit_logs table for tracking security-sensitive
operations (logins, user changes, API key management, etc.).

Created: 2026-03-03
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def upgrade(engine: AsyncEngine) -> None:
    """Apply the migration."""
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                tenant_id UUID NOT NULL,
                actor_id UUID,
                actor_type VARCHAR(20) NOT NULL DEFAULT 'user',
                actor_display VARCHAR(255),
                action VARCHAR(50) NOT NULL,
                resource_type VARCHAR(50),
                resource_id UUID,
                resource_display VARCHAR(255),
                details JSONB,
                ip_address VARCHAR(45),
                user_agent TEXT,
                correlation_id VARCHAR(36),
                success BOOLEAN NOT NULL DEFAULT TRUE,
                error_message TEXT
            )
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant_id ON audit_logs(tenant_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_audit_logs_actor_id ON audit_logs(actor_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_audit_logs_correlation_id ON audit_logs(correlation_id)
        """))


async def downgrade(engine: AsyncEngine) -> None:
    """Revert the migration."""
    async with engine.begin() as conn:
        await conn.execute(text("DROP INDEX IF EXISTS idx_audit_logs_correlation_id"))
        await conn.execute(text("DROP INDEX IF EXISTS idx_audit_logs_action"))
        await conn.execute(text("DROP INDEX IF EXISTS idx_audit_logs_actor_id"))
        await conn.execute(text("DROP INDEX IF EXISTS idx_audit_logs_tenant_id"))
        await conn.execute(text("DROP INDEX IF EXISTS idx_audit_logs_timestamp"))
        await conn.execute(text("DROP TABLE IF EXISTS audit_logs"))


if __name__ == "__main__":
    """Run migration manually."""
    import asyncio

    from flowforge_server.db import get_engine

    async def main():
        engine = get_engine()
        print("Running migration: add_audit_logs_table")
        await upgrade(engine)
        print("Migration completed successfully")

    asyncio.run(main())
