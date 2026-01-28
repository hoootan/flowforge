"""Migration runner for FlowForge database.

Runs all pending migrations in order. Migrations are stored in the
server/migrations directory and are run in alphabetical order.

Each migration module must have an `upgrade(engine)` async function.
"""

import importlib
import logging
import os
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from flowforge_server.db.session import get_engine

logger = logging.getLogger(__name__)

# Migrations directory - check environment variable first (for Docker),
# then fall back to relative path (for local development)
_env_migrations_dir = os.environ.get("FLOWFORGE_MIGRATIONS_DIR")
if _env_migrations_dir:
    MIGRATIONS_DIR = Path(_env_migrations_dir)
else:
    # Relative path for local development: src/flowforge_server/db/migrations.py -> migrations/
    MIGRATIONS_DIR = Path(__file__).parent.parent.parent.parent.parent / "migrations"


async def ensure_migrations_table(engine: AsyncEngine) -> None:
    """Ensure the migrations tracking table exists."""
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS _migrations (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE,
                applied_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
        """))


async def get_applied_migrations(engine: AsyncEngine) -> set[str]:
    """Get the set of already applied migration names."""
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT name FROM _migrations"))
        return {row[0] for row in result.fetchall()}


async def mark_migration_applied(engine: AsyncEngine, name: str) -> None:
    """Mark a migration as applied."""
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO _migrations (name) VALUES (:name)"),
            {"name": name}
        )


async def run_migrations() -> None:
    """Run all pending migrations in order."""
    engine = get_engine()

    # Ensure migrations table exists
    await ensure_migrations_table(engine)

    # Get already applied migrations
    applied = await get_applied_migrations(engine)

    # Find migration files
    if not MIGRATIONS_DIR.exists():
        logger.warning(f"Migrations directory not found: {MIGRATIONS_DIR}")
        return

    migration_files = sorted(MIGRATIONS_DIR.glob("*.py"))

    if not migration_files:
        logger.info("No migration files found")
        return

    # Run pending migrations
    for migration_file in migration_files:
        if migration_file.name.startswith("_"):
            continue

        migration_name = migration_file.stem

        if migration_name in applied:
            logger.debug(f"Migration already applied: {migration_name}")
            continue

        logger.info(f"Running migration: {migration_name}")

        try:
            # Import the migration module
            spec = importlib.util.spec_from_file_location(migration_name, migration_file)
            if spec is None or spec.loader is None:
                logger.error(f"Could not load migration: {migration_name}")
                continue

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Run the upgrade function
            if hasattr(module, "upgrade"):
                await module.upgrade(engine)
                await mark_migration_applied(engine, migration_name)
                logger.info(f"Migration completed: {migration_name}")
            else:
                logger.warning(f"Migration has no upgrade function: {migration_name}")

        except Exception as e:
            logger.error(f"Migration failed: {migration_name} - {e}")
            raise

    logger.info("All migrations completed")
