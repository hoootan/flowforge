"""
Migration: Add serverless/inline execution support

This migration adds:
1. New columns to functions table for inline/serverless execution
2. A new tools table for reusable AI tools

Created: 2026-01-24
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def upgrade(engine: AsyncEngine) -> None:
    """Apply the migration."""
    async with engine.begin() as conn:
        # Add serverless columns to functions table
        await conn.execute(text("""
            ALTER TABLE functions
            ADD COLUMN IF NOT EXISTS is_inline BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS system_prompt TEXT,
            ADD COLUMN IF NOT EXISTS tools_config JSONB,
            ADD COLUMN IF NOT EXISTS agent_config JSONB
        """))

        # Make endpoint_url nullable (for inline functions)
        await conn.execute(text("""
            ALTER TABLE functions
            ALTER COLUMN endpoint_url DROP NOT NULL
        """))

        # Create index for is_inline
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_functions_is_inline ON functions(is_inline)
        """))

        # Create tools table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tools (
                id UUID PRIMARY KEY,
                tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                description TEXT NOT NULL,
                parameters JSONB NOT NULL DEFAULT '{}',
                code TEXT,
                is_builtin BOOLEAN NOT NULL DEFAULT FALSE,
                requires_approval BOOLEAN NOT NULL DEFAULT FALSE,
                approval_timeout VARCHAR(50),
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                CONSTRAINT uq_tool_tenant_name UNIQUE (tenant_id, name)
            )
        """))

        # Create indexes for tools table
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_tools_tenant_id ON tools(tenant_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_tools_name ON tools(name)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_tools_is_builtin ON tools(is_builtin)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_tools_is_active ON tools(is_active)
        """))


async def downgrade(engine: AsyncEngine) -> None:
    """Revert the migration."""
    async with engine.begin() as conn:
        # Drop tools table
        await conn.execute(text("""
            DROP TABLE IF EXISTS tools
        """))

        # Drop index on functions
        await conn.execute(text("""
            DROP INDEX IF EXISTS idx_functions_is_inline
        """))

        # Remove serverless columns from functions table
        await conn.execute(text("""
            ALTER TABLE functions
            DROP COLUMN IF EXISTS agent_config,
            DROP COLUMN IF EXISTS tools_config,
            DROP COLUMN IF EXISTS system_prompt,
            DROP COLUMN IF EXISTS is_inline
        """))

        # Make endpoint_url required again (if reverting)
        # Note: This will fail if there are functions with NULL endpoint_url
        # await conn.execute(text("""
        #     ALTER TABLE functions
        #     ALTER COLUMN endpoint_url SET NOT NULL
        # """))


if __name__ == "__main__":
    """Run migration manually."""
    import asyncio

    from flowforge_server.db import get_engine

    async def main():
        engine = get_engine()
        print("Running migration: add_serverless_support")
        await upgrade(engine)
        print("Migration completed successfully")

    asyncio.run(main())
