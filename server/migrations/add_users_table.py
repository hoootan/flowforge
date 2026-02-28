"""
Migration: Add users table

This migration adds:
1. A new users table for dashboard authentication
2. User roles (admin, member, viewer)
3. Appropriate indexes for performance

Created: 2026-01-28
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def upgrade(engine: AsyncEngine) -> None:
    """Apply the migration."""
    async with engine.begin() as conn:
        # Create users table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                email VARCHAR(255) NOT NULL,
                password_hash TEXT NOT NULL,
                name VARCHAR(255) NOT NULL,
                role VARCHAR(20) NOT NULL DEFAULT 'member',
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                last_login_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                UNIQUE(tenant_id, email)
            )
        """))

        # Create indexes
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_users_tenant_id ON users(tenant_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active)
        """))


async def downgrade(engine: AsyncEngine) -> None:
    """Revert the migration."""
    async with engine.begin() as conn:
        # Drop indexes
        await conn.execute(text("DROP INDEX IF EXISTS idx_users_is_active"))
        await conn.execute(text("DROP INDEX IF EXISTS idx_users_role"))
        await conn.execute(text("DROP INDEX IF EXISTS idx_users_email"))
        await conn.execute(text("DROP INDEX IF EXISTS idx_users_tenant_id"))

        # Drop table
        await conn.execute(text("DROP TABLE IF EXISTS users"))


if __name__ == "__main__":
    """Run migration manually."""
    import asyncio

    from flowforge_server.db import get_engine

    async def main():
        engine = get_engine()
        print("Running migration: add_users_table")
        await upgrade(engine)
        print("Migration completed successfully")

    asyncio.run(main())
