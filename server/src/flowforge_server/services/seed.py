"""Database seeding utilities.

Seeds the database with built-in tools and default data on startup.
"""

import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge_server.db import get_session_context
from flowforge_server.db.models import Tool, Tenant, ApiKey, ApiKeyType, DEFAULT_SCOPES
from flowforge_server.services.builtin_tools import get_builtin_tool_definitions
from flowforge_server.services.auth import generate_api_key, hash_api_key


async def seed_builtin_tools() -> None:
    """Seed built-in tools into the database if they don't exist."""
    print("[Seed] Checking built-in tools...")

    async with get_session_context() as session:
        definitions = get_builtin_tool_definitions()
        created_count = 0
        updated_count = 0

        for tool_def in definitions:
            # Check if tool already exists
            result = await session.execute(
                select(Tool).where(
                    Tool.is_builtin == True,
                    Tool.name == tool_def.name,
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing tool
                existing.description = tool_def.description
                existing.parameters = tool_def.parameters
                existing.requires_approval = tool_def.requires_approval
                existing.approval_timeout = tool_def.approval_timeout
                existing.is_active = True
                updated_count += 1
            else:
                # Create new tool
                tool = Tool(
                    tenant_id=None,  # Built-in tools have no tenant
                    name=tool_def.name,
                    description=tool_def.description,
                    parameters=tool_def.parameters,
                    code=None,  # Built-in tools use Python implementations
                    is_builtin=True,
                    requires_approval=tool_def.requires_approval,
                    approval_timeout=tool_def.approval_timeout,
                    is_active=True,
                )
                session.add(tool)
                created_count += 1

        await session.commit()

        if created_count > 0 or updated_count > 0:
            print(f"[Seed] Built-in tools: {created_count} created, {updated_count} updated")
        else:
            print("[Seed] Built-in tools: already up to date")


async def seed_default_tenant() -> None:
    """Ensure the default tenant exists."""
    print("[Seed] Checking default tenant...")

    async with get_session_context() as session:
        default_tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

        result = await session.execute(
            select(Tenant).where(Tenant.id == default_tenant_id)
        )
        existing = result.scalar_one_or_none()

        if not existing:
            # Create default tenant
            tenant = Tenant(
                id=default_tenant_id,
                name="Default Tenant",
                slug="default",
                api_key_hash="dev_key_hash",  # Placeholder - should be properly hashed
                signing_key_hash="dev_signing_key_hash",  # Placeholder
                settings={},
            )
            session.add(tenant)
            await session.commit()
            print("[Seed] Default tenant created")
        else:
            print("[Seed] Default tenant already exists")


async def seed_default_api_key() -> None:
    """
    Ensure a default API key exists for development.

    Creates a test API key with a well-known value for development use.
    The key is: ff_test_development_key_do_not_use_in_production
    """
    print("[Seed] Checking default API key...")

    async with get_session_context() as session:
        default_tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

        # Check if default tenant exists
        result = await session.execute(
            select(Tenant).where(Tenant.id == default_tenant_id)
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            print("[Seed] Default tenant not found, skipping API key creation")
            return

        # Check if any API key exists for this tenant
        result = await session.execute(
            select(ApiKey).where(
                ApiKey.tenant_id == default_tenant_id,
                ApiKey.is_active == True,
            )
        )
        existing_key = result.scalar_one_or_none()

        if existing_key:
            print("[Seed] Default API key already exists")
            return

        # Create a development API key with a well-known value
        # WARNING: This is for development only! In production, use randomly generated keys.
        dev_key = "ff_test_development_key_do_not_use_in_production"
        key_hash = hash_api_key(dev_key)
        key_prefix = dev_key[:16]

        api_key = ApiKey(
            tenant_id=default_tenant_id,
            name="Development Key",
            key_hash=key_hash,
            key_prefix=key_prefix,
            key_type=ApiKeyType.TEST.value,
            scopes=DEFAULT_SCOPES[ApiKeyType.TEST],
        )

        session.add(api_key)
        await session.commit()

        print(f"[Seed] Default API key created: {dev_key}")
        print("[Seed] WARNING: This key is for development only!")


async def run_all_seeds() -> None:
    """Run all database seeds."""
    await seed_default_tenant()
    await seed_default_api_key()
    await seed_builtin_tools()
    print("[Seed] Database seeding complete")
