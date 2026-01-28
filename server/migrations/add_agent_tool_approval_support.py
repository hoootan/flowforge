"""
Migration: Add agent tool approval support

This migration adds:
1. Tool-specific columns to the steps table
2. A new tool_approvals table for Human-in-the-Loop approval
3. Appropriate indexes for performance

Created: 2026-01-23
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def upgrade(engine: AsyncEngine) -> None:
    """Apply the migration."""
    async with engine.begin() as conn:
        # Add tool-specific columns to steps table
        await conn.execute(text("""
            ALTER TABLE steps
            ADD COLUMN IF NOT EXISTS tool_name VARCHAR(255),
            ADD COLUMN IF NOT EXISTS tool_call_id VARCHAR(255),
            ADD COLUMN IF NOT EXISTS tool_input JSONB,
            ADD COLUMN IF NOT EXISTS tool_output JSONB,
            ADD COLUMN IF NOT EXISTS agent_state JSONB
        """))

        # Create indexes for tool columns
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_steps_tool_name ON steps(tool_name)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_steps_tool_call_id ON steps(tool_call_id)
        """))

        # Create tool_approvals table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tool_approvals (
                id UUID PRIMARY KEY,
                run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
                step_id UUID NOT NULL REFERENCES steps(id) ON DELETE CASCADE,
                tool_name VARCHAR(255) NOT NULL,
                tool_call_id VARCHAR(255) NOT NULL,
                tool_arguments JSONB NOT NULL DEFAULT '{}',
                status VARCHAR(50) NOT NULL DEFAULT 'pending',
                requested_at TIMESTAMP WITH TIME ZONE NOT NULL,
                timeout_at TIMESTAMP WITH TIME ZONE NOT NULL,
                resolved_at TIMESTAMP WITH TIME ZONE,
                resolved_by VARCHAR(255),
                rejection_reason TEXT,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
        """))

        # Create indexes for tool_approvals
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_tool_approvals_run_id ON tool_approvals(run_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_tool_approvals_step_id ON tool_approvals(step_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_tool_approvals_tool_name ON tool_approvals(tool_name)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_tool_approvals_tool_call_id ON tool_approvals(tool_call_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_tool_approvals_status ON tool_approvals(status)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_tool_approvals_timeout_at ON tool_approvals(timeout_at)
        """))


async def downgrade(engine: AsyncEngine) -> None:
    """Revert the migration."""
    async with engine.begin() as conn:
        # Drop tool_approvals table
        await conn.execute(text("""
            DROP TABLE IF EXISTS tool_approvals
        """))

        # Drop indexes on steps table
        await conn.execute(text("""
            DROP INDEX IF EXISTS idx_steps_tool_call_id
        """))
        await conn.execute(text("""
            DROP INDEX IF EXISTS idx_steps_tool_name
        """))

        # Remove tool-specific columns from steps table
        await conn.execute(text("""
            ALTER TABLE steps
            DROP COLUMN IF EXISTS agent_state,
            DROP COLUMN IF EXISTS tool_output,
            DROP COLUMN IF EXISTS tool_input,
            DROP COLUMN IF EXISTS tool_call_id,
            DROP COLUMN IF EXISTS tool_name
        """))


if __name__ == "__main__":
    """Run migration manually."""
    import asyncio
    from flowforge_server.db import get_engine

    async def main():
        engine = get_engine()
        print("Running migration: add_agent_tool_approval_support")
        await upgrade(engine)
        print("Migration completed successfully")

    asyncio.run(main())
