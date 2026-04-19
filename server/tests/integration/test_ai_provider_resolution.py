"""Integration tests for dashboard-only LLM provider credential resolution.

Covers the contract that the ``ai_providers`` table is the single source of
truth at run time: env vars are ignored, rotation propagates immediately,
and missing credentials raise :class:`ProviderNotConfiguredError`.
"""

from __future__ import annotations

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge_server.db.models import AIProvider, Tenant
from flowforge_server.services.ai import AIService
from flowforge_server.services.ai_provider import get_ai_provider_service
from flowforge_server.services.providers import (
    ProviderNotConfiguredError,
    ProviderRegistry,
)


@pytest.fixture(autouse=True)
def encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fernet needs a key. Also reset the cached Fernet between tests."""
    monkeypatch.setenv(
        "FLOWFORGE_ENCRYPTION_KEY", "test-key-for-provider-resolution-suite"
    )
    from flowforge_server.services import crypto
    crypto.clear_cache()


@pytest.fixture(autouse=True)
def reset_provider_cache() -> None:
    """Ensure the in-memory decrypted-key cache is empty per test."""
    get_ai_provider_service().clear_all_cache()


@pytest_asyncio.fixture
async def anthropic_provider(
    test_session: AsyncSession, test_tenant: Tenant
) -> AIProvider:
    service = get_ai_provider_service()
    provider = await service.create_provider(
        session=test_session,
        tenant_id=test_tenant.id,
        provider_name="anthropic",
        api_key="sk-ant-dashboard-original",
        display_name="Dashboard Anthropic",
        is_default=True,
    )
    await test_session.commit()
    await test_session.refresh(provider)
    return provider


@pytest.mark.asyncio
class TestProviderResolution:
    """Exercises ``ProviderRegistry.get_api_key_for_tenant``."""

    async def test_dashboard_provider_resolves(
        self,
        test_session: AsyncSession,
        test_tenant: Tenant,
        anthropic_provider: AIProvider,
    ) -> None:
        registry = ProviderRegistry()
        resolved = await registry.get_api_key_for_tenant(
            test_session, test_tenant.id, "anthropic"
        )
        assert resolved.credential == "sk-ant-dashboard-original"
        assert resolved.provider_id == anthropic_provider.id
        assert resolved.auth_type == "api_key"

    async def test_missing_provider_raises(
        self, test_session: AsyncSession, test_tenant: Tenant
    ) -> None:
        registry = ProviderRegistry()
        with pytest.raises(ProviderNotConfiguredError) as exc_info:
            await registry.get_api_key_for_tenant(
                test_session, test_tenant.id, "anthropic"
            )
        assert exc_info.value.provider == "anthropic"
        assert "anthropic" in str(exc_info.value)
        assert "/settings/ai-providers" in str(exc_info.value)

    async def test_env_var_is_ignored(
        self,
        test_session: AsyncSession,
        test_tenant: Tenant,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Setting the legacy env var must not satisfy resolution.
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-from-env-should-be-ignored")
        registry = ProviderRegistry()

        with pytest.raises(ProviderNotConfiguredError):
            await registry.get_api_key_for_tenant(
                test_session, test_tenant.id, "anthropic"
            )

    async def test_env_var_does_not_override_dashboard(
        self,
        test_session: AsyncSession,
        test_tenant: Tenant,
        anthropic_provider: AIProvider,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-env-should-never-win")
        registry = ProviderRegistry()
        resolved = await registry.get_api_key_for_tenant(
            test_session, test_tenant.id, "anthropic"
        )
        assert resolved.credential == "sk-ant-dashboard-original"

    async def test_rotation_invalidates_cache(
        self,
        test_session: AsyncSession,
        test_tenant: Tenant,
        anthropic_provider: AIProvider,
    ) -> None:
        registry = ProviderRegistry()
        first = await registry.get_api_key_for_tenant(
            test_session, test_tenant.id, "anthropic"
        )
        assert first.credential == "sk-ant-dashboard-original"

        service = get_ai_provider_service()
        await service.rotate_key(
            session=test_session,
            tenant_id=test_tenant.id,
            provider_id=anthropic_provider.id,
            new_api_key="sk-ant-dashboard-rotated",
        )
        await test_session.commit()

        second = await registry.get_api_key_for_tenant(
            test_session, test_tenant.id, "anthropic"
        )
        assert second.credential == "sk-ant-dashboard-rotated"

    async def test_delete_removes_resolution(
        self,
        test_session: AsyncSession,
        test_tenant: Tenant,
        anthropic_provider: AIProvider,
    ) -> None:
        registry = ProviderRegistry()
        await registry.get_api_key_for_tenant(
            test_session, test_tenant.id, "anthropic"
        )

        service = get_ai_provider_service()
        await service.delete_provider(
            test_session, test_tenant.id, anthropic_provider.id
        )
        await test_session.commit()

        with pytest.raises(ProviderNotConfiguredError):
            await registry.get_api_key_for_tenant(
                test_session, test_tenant.id, "anthropic"
            )

    async def test_newly_created_provider_clears_stale_cache(
        self, test_session: AsyncSession, test_tenant: Tenant
    ) -> None:
        """Create-after-miss must replace any cached 'miss' state."""
        registry = ProviderRegistry()

        # Prime the negative path — this should raise.
        with pytest.raises(ProviderNotConfiguredError):
            await registry.get_api_key_for_tenant(
                test_session, test_tenant.id, "anthropic"
            )

        # Now add one — the next lookup must see it.
        service = get_ai_provider_service()
        await service.create_provider(
            session=test_session,
            tenant_id=test_tenant.id,
            provider_name="anthropic",
            api_key="sk-ant-fresh",
            display_name="Fresh",
            is_default=True,
        )
        await test_session.commit()

        resolved = await registry.get_api_key_for_tenant(
            test_session, test_tenant.id, "anthropic"
        )
        assert resolved.credential == "sk-ant-fresh"


@pytest.mark.asyncio
class TestAIServiceIntegration:
    """End-to-end through ``AIService.complete`` with a stubbed litellm."""

    async def test_complete_uses_dashboard_key_and_stamps_last_used(
        self,
        test_session: AsyncSession,
        test_tenant: Tenant,
        anthropic_provider: AIProvider,
    ) -> None:
        registry = ProviderRegistry()
        ai_service = AIService(provider_registry=registry)

        fake_response = MagicMock()
        fake_response.model = "claude-sonnet-4-6"
        fake_response.usage = MagicMock(
            prompt_tokens=10, completion_tokens=20, total_tokens=30
        )
        fake_response.choices = [
            MagicMock(
                finish_reason="stop",
                message=MagicMock(content="ok", tool_calls=None),
            )
        ]

        captured: dict[str, object] = {}

        async def fake_acompletion(**kwargs):
            captured.update(kwargs)
            return fake_response

        fake_litellm = MagicMock()
        fake_litellm.acompletion = AsyncMock(side_effect=fake_acompletion)
        fake_litellm.drop_params = True

        with patch(
            "flowforge_server.services.ai._get_litellm", return_value=fake_litellm
        ):
            result = await ai_service.complete(
                model="claude-sonnet-4-6",
                messages=[{"role": "user", "content": "hi"}],
                tenant_id=test_tenant.id,
                session=test_session,
                use_cache=False,
            )

        assert result.content == "ok"
        assert captured.get("api_key") == "sk-ant-dashboard-original"

        # last_used_at is updated in a fire-and-forget task; give it a tick
        # and check via a fresh read.
        for _ in range(20):
            await asyncio.sleep(0.05)
            await test_session.refresh(anthropic_provider)
            if anthropic_provider.last_used_at is not None:
                break
        assert anthropic_provider.last_used_at is not None

    async def test_complete_raises_when_provider_missing(
        self,
        test_session: AsyncSession,
        test_tenant: Tenant,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Even with env var set, resolution must fail without a dashboard row.
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-ignored")

        registry = ProviderRegistry()
        ai_service = AIService(provider_registry=registry)

        fake_litellm = MagicMock()
        fake_litellm.acompletion = AsyncMock()
        fake_litellm.drop_params = True

        with patch(
            "flowforge_server.services.ai._get_litellm", return_value=fake_litellm
        ):
            with pytest.raises(ProviderNotConfiguredError):
                await ai_service.complete(
                    model="claude-sonnet-4-6",
                    messages=[{"role": "user", "content": "hi"}],
                    tenant_id=test_tenant.id,
                    session=test_session,
                    use_cache=False,
                )

        fake_litellm.acompletion.assert_not_called()


def test_get_api_key_from_env_is_removed() -> None:
    """The legacy env-only helper must be gone."""
    registry = ProviderRegistry()
    assert not hasattr(registry, "get_api_key_from_env")
