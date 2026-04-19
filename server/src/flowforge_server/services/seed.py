"""Database seeding utilities.

Seeds the database with built-in tools and default data on startup.
"""

import os
import uuid

from sqlalchemy import func, select

from flowforge_server.db import get_session_context
from flowforge_server.db.models import DEFAULT_SCOPES, AIProvider, ApiKey, ApiKeyType, Tenant, Tool
from flowforge_server.services.auth import hash_api_key
from flowforge_server.services.builtin_tools import get_builtin_tool_definitions


async def seed_builtin_tools() -> None:
    """Seed built-in tools into the database, removing stale ones."""
    print("[Seed] Checking built-in tools...")

    async with get_session_context() as session:
        definitions = get_builtin_tool_definitions()
        valid_names = {d.name for d in definitions}
        created_count = 0
        updated_count = 0
        removed_count = 0

        # Remove stale built-in tools no longer in definitions
        result = await session.execute(
            select(Tool).where(Tool.is_builtin == True)
        )
        existing_builtins = list(result.scalars().all())

        for tool in existing_builtins:
            if tool.name not in valid_names:
                await session.delete(tool)
                removed_count += 1
                print(f"[Seed] Removed stale built-in tool: {tool.name}")

        # Create or update current definitions
        for tool_def in definitions:
            result = await session.execute(
                select(Tool).where(
                    Tool.is_builtin == True,
                    Tool.name == tool_def.name,
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                existing.description = tool_def.description
                existing.parameters = tool_def.parameters
                existing.requires_approval = tool_def.requires_approval
                existing.approval_timeout = tool_def.approval_timeout
                existing.tool_type = "builtin"
                existing.is_active = True
                updated_count += 1
            else:
                tool = Tool(
                    tenant_id=None,
                    name=tool_def.name,
                    description=tool_def.description,
                    parameters=tool_def.parameters,
                    tool_type="builtin",
                    code=None,
                    is_builtin=True,
                    requires_approval=tool_def.requires_approval,
                    approval_timeout=tool_def.approval_timeout,
                    is_active=True,
                )
                session.add(tool)
                created_count += 1

        await session.commit()

        parts = []
        if created_count:
            parts.append(f"{created_count} created")
        if updated_count:
            parts.append(f"{updated_count} updated")
        if removed_count:
            parts.append(f"{removed_count} removed")
        if parts:
            print(f"[Seed] Built-in tools: {', '.join(parts)}")
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
            ).limit(1)
        )
        existing_key = result.scalar_one_or_none()

        if existing_key:
            print("[Seed] API keys already exist, skipping default key creation")
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


_LLM_ENV_VARS: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "cohere": "COHERE_API_KEY",
}


async def warn_if_no_llm_providers() -> None:
    """Log a loud warning when the default tenant has no AI providers.

    Also call out any legacy ``*_API_KEY`` env vars that were the old
    configuration surface — those are no longer consulted at runtime.
    """
    default_tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    async with get_session_context() as session:
        count = (
            await session.execute(
                select(func.count())
                .select_from(AIProvider)
                .where(
                    AIProvider.tenant_id == default_tenant_id,
                    AIProvider.is_active == True,  # noqa: E712
                )
            )
        ).scalar_one()

    ignored_env_vars = [
        env for env in _LLM_ENV_VARS.values() if os.environ.get(env)
    ]

    if count == 0:
        print(
            "[Seed] WARNING: No LLM providers configured. AI steps will fail "
            "until one is added at /settings?tab=ai-providers."
        )

    if ignored_env_vars:
        joined = ", ".join(sorted(ignored_env_vars))
        print(
            "[Seed] WARNING: Ignoring legacy LLM env vars at runtime "
            f"({joined}). Configure providers at "
            "/settings?tab=ai-providers instead."
        )


async def run_all_seeds() -> None:
    """Run all database seeds."""
    await seed_default_tenant()
    await seed_default_api_key()
    await seed_builtin_tools()
    await warn_if_no_llm_providers()
    print("[Seed] Database seeding complete")
