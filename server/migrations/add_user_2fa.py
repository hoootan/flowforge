"""
Migration: Add 2FA fields to users table

This migration adds:
1. totp_secret - Encrypted TOTP secret for 2FA
2. totp_enabled - Whether 2FA is enabled for this user
3. backup_codes - Encrypted backup codes for 2FA recovery

Created: 2026-01-31
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def upgrade(engine: AsyncEngine) -> None:
    """Apply the migration."""
    async with engine.begin() as conn:
        # Add totp_secret column
        await conn.execute(text("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS totp_secret TEXT
        """))

        # Add totp_enabled column
        await conn.execute(text("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS totp_enabled BOOLEAN NOT NULL DEFAULT FALSE
        """))

        # Add backup_codes column (array of encrypted backup codes)
        await conn.execute(text("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS backup_codes VARCHAR(64)[]
        """))

        # Add comment to columns
        await conn.execute(text("""
            COMMENT ON COLUMN users.totp_secret IS 'Encrypted TOTP secret for 2FA'
        """))
        await conn.execute(text("""
            COMMENT ON COLUMN users.totp_enabled IS 'Whether 2FA is enabled for this user'
        """))
        await conn.execute(text("""
            COMMENT ON COLUMN users.backup_codes IS 'Encrypted backup codes for 2FA recovery'
        """))


async def downgrade(engine: AsyncEngine) -> None:
    """Revert the migration."""
    async with engine.begin() as conn:
        # Drop columns
        await conn.execute(text("""
            ALTER TABLE users
            DROP COLUMN IF EXISTS backup_codes
        """))
        await conn.execute(text("""
            ALTER TABLE users
            DROP COLUMN IF EXISTS totp_enabled
        """))
        await conn.execute(text("""
            ALTER TABLE users
            DROP COLUMN IF EXISTS totp_secret
        """))


if __name__ == "__main__":
    """Run migration manually."""
    import asyncio

    from flowforge_server.db import get_engine

    async def main():
        engine = get_engine()
        print("Running migration: add_user_2fa")
        await upgrade(engine)
        print("Migration completed successfully")

    asyncio.run(main())
