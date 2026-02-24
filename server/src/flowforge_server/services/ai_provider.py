"""AI Provider service for managing encrypted AI credentials.

Provides CRUD operations for per-tenant AI provider configurations
with encrypted API key storage.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any, TYPE_CHECKING

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge_server.db.models import AIProvider
from flowforge_server.services.crypto import (
    encrypt_value,
    decrypt_value,
    get_key_prefix,
    EncryptionError,
)

if TYPE_CHECKING:
    pass


# Known provider configurations
KNOWN_PROVIDERS = {
    "openai": {
        "display_name": "OpenAI",
        "models": ["gpt-5.3", "gpt-5.2", "o3", "o4-mini", "o3-mini"],
        "default_model": "gpt-5.3",
    },
    "anthropic": {
        "display_name": "Anthropic",
        "models": [
            "claude-opus-4-6",
            "claude-sonnet-4-6",
            "claude-haiku-4-5-20251001",
        ],
        "default_model": "claude-sonnet-4-6",
    },
    "google": {
        "display_name": "Google AI",
        "models": ["gemini-3.1-pro", "gemini-3-pro", "gemini-3-flash", "gemini-2.5-flash"],
        "default_model": "gemini-3.1-pro",
    },
    "mistral": {
        "display_name": "Mistral AI",
        "models": ["mistral-large-latest", "mistral-medium-latest", "mistral-small-latest"],
        "default_model": "mistral-large-latest",
    },
    "cohere": {
        "display_name": "Cohere",
        "models": ["command-r-plus", "command-r", "command"],
        "default_model": "command-r-plus",
    },
    "custom": {
        "display_name": "Custom Provider",
        "models": [],
        "default_model": None,
    },
}


class AIProviderError(Exception):
    """Base exception for AI provider operations."""

    pass


class AIProviderNotFoundError(AIProviderError):
    """Raised when a provider is not found."""

    pass


class AIProviderExistsError(AIProviderError):
    """Raised when trying to create a duplicate provider."""

    pass


class AIProviderService:
    """
    Service for managing AI provider configurations.

    Handles encrypted storage of API keys and per-tenant provider management.
    """

    # In-memory cache for decrypted keys (tenant_id:provider -> (key, auth_type, expiry))
    _key_cache: dict[str, tuple[str, str, datetime]] = {}
    _cache_ttl = timedelta(minutes=5)

    async def create_provider(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        provider_name: str,
        api_key: str,
        display_name: str | None = None,
        base_url: str | None = None,
        is_default: bool = False,
        config: dict[str, Any] | None = None,
        auth_type: str = "api_key",
    ) -> AIProvider:
        """
        Create a new AI provider configuration.

        Args:
            session: Database session
            tenant_id: Tenant ID
            provider_name: Provider identifier (openai, anthropic, etc.)
            api_key: The API key or OAuth token (will be encrypted)
            display_name: User-friendly name (defaults to provider's standard name)
            base_url: Optional custom API endpoint
            is_default: Whether this should be the default provider
            config: Additional configuration
            auth_type: Authentication type ("api_key" or "oauth_token")

        Returns:
            The created AIProvider

        Raises:
            AIProviderExistsError: If provider already exists for this tenant
        """
        # Check if provider already exists
        existing = await self.get_provider(
            session, tenant_id, provider_name, raise_not_found=False
        )
        if existing:
            raise AIProviderExistsError(
                f"Provider '{provider_name}' already exists for this tenant. "
                "Use update_provider to modify it."
            )

        # Set default display name
        if not display_name:
            provider_info = KNOWN_PROVIDERS.get(provider_name, {})
            display_name = provider_info.get("display_name", provider_name.title())

        # Encrypt the API key / OAuth token
        api_key_encrypted = encrypt_value(api_key)
        api_key_prefix = get_key_prefix(api_key)

        # If this is being set as default, unset other defaults
        if is_default:
            await self._clear_default_provider(session, tenant_id)

        # Create the provider
        provider = AIProvider(
            tenant_id=tenant_id,
            provider_name=provider_name.lower(),
            display_name=display_name,
            api_key_encrypted=api_key_encrypted,
            api_key_prefix=api_key_prefix,
            auth_type=auth_type,
            base_url=base_url,
            is_default=is_default,
            config=config or {},
        )

        session.add(provider)
        return provider

    async def get_provider(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        provider_name: str,
        raise_not_found: bool = True,
    ) -> AIProvider | None:
        """
        Get a provider by tenant and name.

        Args:
            session: Database session
            tenant_id: Tenant ID
            provider_name: Provider identifier
            raise_not_found: If True, raise exception when not found

        Returns:
            The AIProvider or None

        Raises:
            AIProviderNotFoundError: If provider not found and raise_not_found is True
        """
        result = await session.execute(
            select(AIProvider).where(
                AIProvider.tenant_id == tenant_id,
                AIProvider.provider_name == provider_name.lower(),
            )
        )
        provider = result.scalar_one_or_none()

        if not provider and raise_not_found:
            raise AIProviderNotFoundError(
                f"Provider '{provider_name}' not found for this tenant"
            )

        return provider

    async def get_provider_by_id(
        self,
        session: AsyncSession,
        provider_id: uuid.UUID,
        tenant_id: uuid.UUID | None = None,
    ) -> AIProvider | None:
        """
        Get a provider by ID.

        Args:
            session: Database session
            provider_id: Provider ID
            tenant_id: Optional tenant ID for validation

        Returns:
            The AIProvider or None
        """
        query = select(AIProvider).where(AIProvider.id == provider_id)
        if tenant_id:
            query = query.where(AIProvider.tenant_id == tenant_id)

        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def list_providers(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        include_inactive: bool = False,
    ) -> list[AIProvider]:
        """
        List all providers for a tenant.

        Args:
            session: Database session
            tenant_id: Tenant ID
            include_inactive: Whether to include inactive providers

        Returns:
            List of AIProvider objects (keys are NOT decrypted)
        """
        query = select(AIProvider).where(AIProvider.tenant_id == tenant_id)

        if not include_inactive:
            query = query.where(AIProvider.is_active == True)

        query = query.order_by(AIProvider.is_default.desc(), AIProvider.provider_name)

        result = await session.execute(query)
        return list(result.scalars().all())

    async def update_provider(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        provider_name: str,
        api_key: str | None = None,
        display_name: str | None = None,
        base_url: str | None = None,
        is_active: bool | None = None,
        is_default: bool | None = None,
        config: dict[str, Any] | None = None,
        auth_type: str | None = None,
    ) -> AIProvider:
        """
        Update an existing provider.

        Args:
            session: Database session
            tenant_id: Tenant ID
            provider_name: Provider identifier
            api_key: New API key or OAuth token (will be encrypted)
            display_name: New display name
            base_url: New base URL (pass "" to clear)
            is_active: New active status
            is_default: New default status
            config: New configuration (replaces existing)
            auth_type: New authentication type ("api_key" or "oauth_token")

        Returns:
            Updated AIProvider

        Raises:
            AIProviderNotFoundError: If provider not found
        """
        provider = await self.get_provider(session, tenant_id, provider_name)

        if api_key is not None:
            provider.api_key_encrypted = encrypt_value(api_key)
            provider.api_key_prefix = get_key_prefix(api_key)
            # Clear cache for this provider
            self._clear_key_cache(tenant_id, provider_name)

        if auth_type is not None:
            provider.auth_type = auth_type
            # Clear cache since auth_type affects how the credential is used
            self._clear_key_cache(tenant_id, provider_name)

        if display_name is not None:
            provider.display_name = display_name

        if base_url is not None:
            provider.base_url = base_url if base_url else None

        if is_active is not None:
            provider.is_active = is_active

        if is_default is not None and is_default != provider.is_default:
            if is_default:
                await self._clear_default_provider(session, tenant_id)
            provider.is_default = is_default

        if config is not None:
            provider.config = config

        return provider

    async def delete_provider(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        provider_name: str,
    ) -> bool:
        """
        Delete a provider.

        Args:
            session: Database session
            tenant_id: Tenant ID
            provider_name: Provider identifier

        Returns:
            True if deleted, False if not found
        """
        # First check if provider exists
        provider = await self.get_provider(session, tenant_id, provider_name, raise_not_found=False)
        if not provider:
            return False

        # Delete the provider
        await session.execute(
            delete(AIProvider).where(
                AIProvider.tenant_id == tenant_id,
                AIProvider.provider_name == provider_name.lower(),
            )
        )

        # Clear cache
        self._clear_key_cache(tenant_id, provider_name)

        return True

    async def get_decrypted_key(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        provider_name: str,
    ) -> tuple[str, str] | None:
        """
        Get the decrypted credential and auth type for a provider.

        Uses in-memory caching to avoid repeated decryption.

        Args:
            session: Database session
            tenant_id: Tenant ID
            provider_name: Provider identifier

        Returns:
            Tuple of (credential, auth_type) or None if not found.
            auth_type is "api_key" or "oauth_token".
        """
        cache_key = f"{tenant_id}:{provider_name.lower()}"

        # Check cache
        if cache_key in self._key_cache:
            key, auth_type, expiry = self._key_cache[cache_key]
            if datetime.utcnow() < expiry:
                return (key, auth_type)
            else:
                del self._key_cache[cache_key]

        # Fetch from database
        provider = await self.get_provider(
            session, tenant_id, provider_name, raise_not_found=False
        )

        if not provider or not provider.is_active:
            return None

        try:
            decrypted = decrypt_value(provider.api_key_encrypted)
            auth_type = provider.auth_type or "api_key"
            # Cache the decrypted key and auth type
            self._key_cache[cache_key] = (decrypted, auth_type, datetime.utcnow() + self._cache_ttl)
            return (decrypted, auth_type)
        except EncryptionError:
            return None

    async def get_default_provider(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> AIProvider | None:
        """
        Get the default provider for a tenant.

        Args:
            session: Database session
            tenant_id: Tenant ID

        Returns:
            The default AIProvider or None
        """
        result = await session.execute(
            select(AIProvider).where(
                AIProvider.tenant_id == tenant_id,
                AIProvider.is_default == True,
                AIProvider.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def test_provider(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        provider_name: str,
    ) -> dict[str, Any]:
        """
        Test a provider's credential connectivity.

        Args:
            session: Database session
            tenant_id: Tenant ID
            provider_name: Provider identifier

        Returns:
            Dict with status and message
        """
        provider = await self.get_provider(session, tenant_id, provider_name)
        result = await self.get_decrypted_key(session, tenant_id, provider_name)

        if not result:
            return {
                "status": "error",
                "message": "Could not decrypt credential",
            }

        credential, auth_type = result

        try:
            # Try a minimal API call to verify the credential works
            import litellm

            # Use a minimal model call based on provider
            test_model = None
            if provider_name == "openai":
                test_model = "gpt-5.2"
            elif provider_name == "anthropic":
                test_model = "claude-haiku-4-5-20251001"
            elif provider_name == "google":
                test_model = "gemini-3-flash"
            elif provider_name == "mistral":
                test_model = "mistral-small-latest"
            else:
                # For custom providers, we can't easily test
                return {
                    "status": "unknown",
                    "message": "Cannot automatically test custom providers",
                }

            # Build completion params based on auth type
            import os
            completion_params: dict[str, Any] = {
                "model": test_model,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 1,
            }

            old_key = None
            env_var = f"{provider_name.upper()}_API_KEY"

            if auth_type == "oauth_token":
                # OAuth tokens go via extra_headers as Bearer token
                completion_params["extra_headers"] = {
                    "Authorization": f"Bearer {credential}"
                }
            else:
                # Standard API key auth via env var
                old_key = os.environ.get(env_var)
                os.environ[env_var] = credential

            try:
                # Make a minimal request (just to test auth)
                response = await litellm.acompletion(**completion_params)
                return {
                    "status": "healthy",
                    "message": f"{'OAuth token' if auth_type == 'oauth_token' else 'API key'} is valid",
                    "model_tested": response.model if hasattr(response, 'model') else test_model,
                }
            finally:
                # Restore original key (only for api_key auth type)
                if auth_type != "oauth_token":
                    if old_key:
                        os.environ[env_var] = old_key
                    elif env_var in os.environ:
                        del os.environ[env_var]

        except ImportError:
            return {
                "status": "unknown",
                "message": "litellm not installed - cannot test connection",
            }
        except Exception as e:
            error_str = str(e).lower()
            if "401" in error_str or "unauthorized" in error_str or "invalid" in error_str:
                return {
                    "status": "error",
                    "message": f"{'OAuth token' if auth_type == 'oauth_token' else 'API key'} is invalid or expired",
                }
            elif "rate" in error_str or "quota" in error_str:
                return {
                    "status": "healthy",
                    "message": f"{'OAuth token' if auth_type == 'oauth_token' else 'API key'} is valid (but rate limited)",
                }
            else:
                return {
                    "status": "error",
                    "message": f"Connection test failed: {str(e)[:100]}",
                }

    async def rotate_key(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        provider_name: str,
        new_api_key: str,
    ) -> AIProvider:
        """
        Rotate the API key for a provider.

        This is essentially an update with just the API key,
        but semantically distinct for audit purposes.

        Args:
            session: Database session
            tenant_id: Tenant ID
            provider_name: Provider identifier
            new_api_key: The new API key

        Returns:
            Updated AIProvider
        """
        return await self.update_provider(
            session=session,
            tenant_id=tenant_id,
            provider_name=provider_name,
            api_key=new_api_key,
        )

    async def _clear_default_provider(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> None:
        """Clear any existing default provider for a tenant."""
        await session.execute(
            update(AIProvider)
            .where(
                AIProvider.tenant_id == tenant_id,
                AIProvider.is_default == True,
            )
            .values(is_default=False)
        )

    def _clear_key_cache(
        self,
        tenant_id: uuid.UUID,
        provider_name: str,
    ) -> None:
        """Clear the cached key for a provider."""
        cache_key = f"{tenant_id}:{provider_name.lower()}"
        if cache_key in self._key_cache:
            del self._key_cache[cache_key]

    def clear_all_cache(self) -> None:
        """Clear all cached keys. Used for testing or key rotation."""
        self._key_cache.clear()


# Global service instance
_ai_provider_service: AIProviderService | None = None


def get_ai_provider_service() -> AIProviderService:
    """Get the global AI provider service instance."""
    global _ai_provider_service
    if _ai_provider_service is None:
        _ai_provider_service = AIProviderService()
    return _ai_provider_service
