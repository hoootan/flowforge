"""Provider management for AI services.

This module provides a unified interface for managing AI providers,
including configuration, health checking, and fallback chains.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from .config import (
    DEFAULT_FALLBACK_CHAINS,
    DEFAULT_MODEL_CONFIGS,
    MODEL_ALIASES,
    FallbackConfig,
    ModelConfig,
    ProviderRegistryConfig,
    ProviderSettings,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from .health import HealthChecker, HealthStatus

__all__ = [
    "ProviderRegistry",
    "ProviderSettings",
    "ModelConfig",
    "FallbackConfig",
    "ProviderRegistryConfig",
    "ResolvedCredential",
    "ProviderNotConfiguredError",
]


@dataclass(frozen=True)
class ResolvedCredential:
    """Credential resolved from the dashboard-stored AIProvider row."""

    credential: str
    auth_type: str
    provider_id: uuid.UUID


class ProviderNotConfiguredError(Exception):
    """Raised when no active AIProvider row exists for the requested provider.

    Carries the provider name so callers can surface an actionable error
    message directing users to the dashboard.
    """

    def __init__(self, provider: str) -> None:
        self.provider = provider
        super().__init__(
            f"No '{provider}' provider is configured for this tenant. "
            "Add one at /settings/ai-providers in the dashboard."
        )


class ProviderRegistry:
    """
    Central registry for AI provider configuration.

    Features:
    - Unified configuration from file, env vars, or code
    - Model aliasing and routing
    - Fallback chain management
    - Health checking integration
    """

    def __init__(
        self,
        config: ProviderRegistryConfig | None = None,
        config_path: str | None = None,
    ) -> None:
        """
        Initialize the provider registry.

        Args:
            config: Direct configuration object
            config_path: Path to YAML configuration file
        """
        self.config = config or self._load_config(config_path)
        self._health_checker: HealthChecker | None = None

    def _load_config(self, path: str | None) -> ProviderRegistryConfig:
        """Load non-credential configuration from file.

        API keys are NOT loaded here. Per-tenant credentials live exclusively
        in the ``ai_providers`` table and are resolved at request time via
        :meth:`get_api_key_for_tenant`.
        """
        config = ProviderRegistryConfig()

        if path and Path(path).exists():
            with open(path) as f:
                data = yaml.safe_load(f)
                if data:
                    config = ProviderRegistryConfig.model_validate(data)

        return config

    def get_model_config(self, model: str) -> ModelConfig:
        """
        Get configuration for a model.

        Args:
            model: Model name or alias

        Returns:
            ModelConfig for the requested model

        Raises:
            ValueError: If model is not found
        """
        # Resolve alias first
        resolved = self.resolve_alias(model)

        # Check custom configs first
        if resolved in self.config.models:
            return self.config.models[resolved]

        # Fall back to defaults
        if resolved in DEFAULT_MODEL_CONFIGS:
            return DEFAULT_MODEL_CONFIGS[resolved]

        # Try to infer from model name
        return self._infer_model_config(resolved)

    def resolve_alias(self, model: str) -> str:
        """
        Resolve a model alias to its actual model ID.

        Args:
            model: Model name or alias

        Returns:
            Resolved model ID
        """
        # Check custom aliases first
        if model in self.config.aliases:
            return self.config.aliases[model]

        # Check default aliases
        if model in MODEL_ALIASES:
            return MODEL_ALIASES[model]

        return model

    def get_provider_settings(self, provider: str) -> ProviderSettings:
        """
        Get settings for a provider.

        Args:
            provider: Provider name (openai, anthropic, etc.)

        Returns:
            ProviderSettings for the provider
        """
        if provider in self.config.providers:
            return self.config.providers[provider]

        # Return default settings
        return ProviderSettings()

    def resolve_model(
        self,
        model: str,
        fallback_chain: str | None = None,
    ) -> tuple[str, ModelConfig, ProviderSettings]:
        """
        Resolve a model to its actual ID, config, and provider settings.

        If fallback_chain is provided and primary model is unhealthy,
        returns next available model in chain.

        Args:
            model: Model name or alias
            fallback_chain: Name of fallback chain to use

        Returns:
            Tuple of (model_id, ModelConfig, ProviderSettings)
        """
        # If no fallback chain or no health checker, just resolve directly
        if not fallback_chain or not self._health_checker:
            resolved = self.resolve_alias(model)
            config = self.get_model_config(resolved)
            settings = self._get_merged_settings(config)
            return resolved, config, settings

        # Get fallback chain
        chain = self.get_fallback_chain(fallback_chain)
        if not chain:
            # No chain found, use model directly
            resolved = self.resolve_alias(model)
            config = self.get_model_config(resolved)
            settings = self._get_merged_settings(config)
            return resolved, config, settings

        # Try each model in chain
        for chain_model in chain.models:
            resolved = self.resolve_alias(chain_model)
            config = self.get_model_config(resolved)

            # Check health
            if self._health_checker.is_healthy(config.provider):
                settings = self._get_merged_settings(config)
                return resolved, config, settings

        # All unhealthy, fall back to first in chain
        first_model = self.resolve_alias(chain.models[0])
        config = self.get_model_config(first_model)
        settings = self._get_merged_settings(config)
        return first_model, config, settings

    def get_fallback_chain(self, name: str) -> FallbackConfig | None:
        """
        Get a fallback chain by name.

        Args:
            name: Chain name

        Returns:
            FallbackConfig or None if not found
        """
        if name in self.config.fallbacks:
            return self.config.fallbacks[name]

        if name in DEFAULT_FALLBACK_CHAINS:
            return DEFAULT_FALLBACK_CHAINS[name]

        return None

    def get_default_model(self, use_case: str = "default") -> str:
        """
        Get the default model for a use case.

        Args:
            use_case: Use case name (default, fast, smart, coding, cheap, reasoning)

        Returns:
            Model name
        """
        if use_case in self.config.defaults:
            return self.config.defaults[use_case]

        # Default fallbacks
        defaults = {
            "default": "gpt-5.3",
            "fast": "gpt-5.2",
            "smart": "gpt-5.3",
            "coding": "claude-sonnet-4-6",
            "cheap": "gemini-2.5-flash",
            "reasoning": "o3",
        }
        return defaults.get(use_case, "gpt-5.3")

    def set_health_checker(self, checker: HealthChecker) -> None:
        """Set the health checker for provider health awareness."""
        self._health_checker = checker

    def calculate_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """
        Calculate cost for a model call (synchronous, uses defaults only).

        Args:
            model: Model name
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        config = self.get_model_config(model)

        input_price = config.input_price_per_m or 1.0
        output_price = config.output_price_per_m or 2.0

        input_cost = (prompt_tokens / 1_000_000) * input_price
        output_cost = (completion_tokens / 1_000_000) * output_price

        return round(input_cost + output_cost, 6)

    async def calculate_cost_async(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """
        Calculate cost for a model call using configurable pricing.

        This async version uses the model pricing service to get tenant-specific
        or global custom pricing, falling back to defaults.

        Args:
            session: Database session
            tenant_id: Tenant ID for tenant-specific pricing
            model: Model name
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        from flowforge_server.services.model_pricing import get_model_pricing_service

        pricing_service = get_model_pricing_service()
        input_price, output_price, source, pricing_id = await pricing_service.get_effective_pricing(
            session, model, tenant_id
        )

        input_cost = (prompt_tokens / 1_000_000) * input_price
        output_cost = (completion_tokens / 1_000_000) * output_price

        return round(input_cost + output_cost, 6)

    def _get_merged_settings(self, config: ModelConfig) -> ProviderSettings:
        """Get merged settings for a model (model-specific + provider-level)."""
        provider_settings = self.get_provider_settings(config.provider)

        if config.settings:
            # Merge model-specific settings over provider settings
            merged = provider_settings.model_copy()
            model_settings = config.settings.model_dump(exclude_unset=True)
            for key, value in model_settings.items():
                if value is not None:
                    setattr(merged, key, value)
            return merged

        return provider_settings

    def _infer_model_config(self, model: str) -> ModelConfig:
        """Infer model config from model name."""
        model_lower = model.lower()

        # Detect provider
        if model_lower.startswith("gpt") or model_lower.startswith("o1"):
            provider = "openai"
        elif model_lower.startswith("claude"):
            provider = "anthropic"
        elif model_lower.startswith("gemini"):
            provider = "google"
        elif model_lower.startswith("mistral"):
            provider = "mistral"
        elif model_lower.startswith("command"):
            provider = "cohere"
        else:
            provider = "unknown"

        return ModelConfig(
            provider=provider,
            model_id=model,
        )

    def list_models(self) -> list[str]:
        """List all available model names."""
        models = set(DEFAULT_MODEL_CONFIGS.keys())
        models.update(self.config.models.keys())
        models.update(MODEL_ALIASES.keys())
        models.update(self.config.aliases.keys())
        return sorted(models)

    def list_providers(self) -> list[str]:
        """List all configured providers."""
        providers = set()
        for config in DEFAULT_MODEL_CONFIGS.values():
            providers.add(config.provider)
        for config in self.config.models.values():
            providers.add(config.provider)
        providers.update(self.config.providers.keys())
        return sorted(providers)

    def to_dict(self) -> dict[str, Any]:
        """Serialize registry config to dict (excludes API keys)."""
        data = self.config.model_dump()
        # Remove sensitive data
        for provider_settings in data.get("providers", {}).values():
            if "api_key" in provider_settings:
                provider_settings["api_key"] = "***"
        return data

    async def get_api_key_for_tenant(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        provider: str,
    ) -> ResolvedCredential:
        """Resolve the credential for a provider from the tenant's dashboard configuration.

        The dashboard (``ai_providers`` table) is the single source of truth. There is no
        environment-variable fallback; missing credentials raise
        :class:`ProviderNotConfiguredError` so callers can surface an actionable message.

        Args:
            session: Database session for querying tenant providers.
            tenant_id: Tenant ID to look up.
            provider: Provider name (openai, anthropic, etc.).

        Returns:
            :class:`ResolvedCredential` with the decrypted credential, its auth type,
            and the source provider row's ID.

        Raises:
            ProviderNotConfiguredError: If no active row exists for this tenant+provider.
        """
        from flowforge_server.services.ai_provider import get_ai_provider_service

        service = get_ai_provider_service()
        result = await service.get_decrypted_key(session, tenant_id, provider)
        if not result:
            raise ProviderNotConfiguredError(provider)

        credential, auth_type, provider_id = result
        return ResolvedCredential(
            credential=credential,
            auth_type=auth_type,
            provider_id=provider_id,
        )


# Global registry instance
_registry: ProviderRegistry | None = None


def get_provider_registry() -> ProviderRegistry:
    """Get the global provider registry instance."""
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
    return _registry


def set_provider_registry(registry: ProviderRegistry) -> None:
    """Set the global provider registry instance."""
    global _registry
    _registry = registry
