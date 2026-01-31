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
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo", "o1-preview", "o1-mini"],
        "default_model": "gpt-4o",
    },
    "anthropic": {
        "display_name": "Anthropic",
        "models": [
            "claude-opus-4-5-20250514",
            "claude-sonnet-4-5-20250514",
            "claude-sonnet-4-20250514",
            "claude-3-5-sonnet-20241022",
            "claude-3-opus-20240229",
            "claude-3-haiku-20240307",
        ],
        "default_model": "claude-sonnet-4-5-20250514",
    },
    "google": {
        "display_name": "Google AI",
        "models": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-pro"],
        "default_model": "gemini-1.5-pro",
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

    # In-memory cache for decrypted keys (tenant_id:provider -> (key, expiry))
    _key_cache: dict[str, tuple[str, datetime]] = {}
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
    ) -> AIProvider:
        """
        Create a new AI provider configuration.

        Args:
            session: Database session
            tenant_id: Tenant ID
            provider_name: Provider identifier (openai, anthropic, etc.)
            api_key: The API key (will be encrypted)
            display_name: User-friendly name (defaults to provider's standard name)
            base_url: Optional custom API endpoint
            is_default: Whether this should be the default provider
            config: Additional configuration

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

        # Encrypt the API key
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
    ) -> AIProvider:
        """
        Update an existing provider.

        Args:
            session: Database session
            tenant_id: Tenant ID
            provider_name: Provider identifier
            api_key: New API key (will be encrypted)
            display_name: New display name
            base_url: New base URL (pass "" to clear)
            is_active: New active status
            is_default: New default status
            config: New configuration (replaces existing)

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
    ) -> str | None:
        """
        Get the decrypted API key for a provider.

        Uses in-memory caching to avoid repeated decryption.

        Args:
            session: Database session
            tenant_id: Tenant ID
            provider_name: Provider identifier

        Returns:
            Decrypted API key or None if not found
        """
        cache_key = f"{tenant_id}:{provider_name.lower()}"

        # Check cache
        if cache_key in self._key_cache:
            key, expiry = self._key_cache[cache_key]
            if datetime.utcnow() < expiry:
                return key
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
            # Cache the decrypted key
            self._key_cache[cache_key] = (decrypted, datetime.utcnow() + self._cache_ttl)
            return decrypted
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
        Test a provider's API key connectivity.

        Args:
            session: Database session
            tenant_id: Tenant ID
            provider_name: Provider identifier

        Returns:
            Dict with status and message
        """
        provider = await self.get_provider(session, tenant_id, provider_name)
        api_key = await self.get_decrypted_key(session, tenant_id, provider_name)

        if not api_key:
            return {
                "status": "error",
                "message": "Could not decrypt API key",
            }

        try:
            # Try a minimal API call to verify the key works
            import litellm

            # Use a minimal model call based on provider
            test_model = None
            if provider_name == "openai":
                test_model = "gpt-3.5-turbo"
            elif provider_name == "anthropic":
                test_model = "claude-3-haiku-20240307"
            elif provider_name == "google":
                test_model = "gemini-pro"
            elif provider_name == "mistral":
                test_model = "mistral-small-latest"
            else:
                # For custom providers, we can't easily test
                return {
                    "status": "unknown",
                    "message": "Cannot automatically test custom providers",
                }

            # Set the API key for this request
            import os
            env_var = f"{provider_name.upper()}_API_KEY"
            old_key = os.environ.get(env_var)
            os.environ[env_var] = api_key

            try:
                # Make a minimal request (just to test auth)
                response = await litellm.acompletion(
                    model=test_model,
                    messages=[{"role": "user", "content": "Hi"}],
                    max_tokens=1,
                )
                return {
                    "status": "healthy",
                    "message": "API key is valid",
                    "model_tested": response.model if hasattr(response, 'model') else test_model,
                }
            finally:
                # Restore original key
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
                    "message": "API key is invalid or expired",
                }
            elif "rate" in error_str or "quota" in error_str:
                return {
                    "status": "healthy",
                    "message": "API key is valid (but rate limited)",
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
