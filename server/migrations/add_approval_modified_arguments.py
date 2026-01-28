"""
Migration: Add modified_arguments to tool_approvals

This migration adds:
1. modified_arguments column to tool_approvals table for storing user input

Created: 2026-01-27
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def upgrade(engine: AsyncEngine) -> None:
    """Apply the migration."""
    async with engine.begin() as conn:
        # Add modified_arguments column to tool_approvals table
        await conn.execute(text("""
            ALTER TABLE tool_approvals
            ADD COLUMN IF NOT EXISTS modified_arguments JSONB
        """))


async def downgrade(engine: AsyncEngine) -> None:
    """Revert the migration."""
    async with engine.begin() as conn:
        await conn.execute(text("""
            ALTER TABLE tool_approvals
            DROP COLUMN IF EXISTS modified_arguments
        """))
