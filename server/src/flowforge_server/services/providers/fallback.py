"""Fallback execution for AI providers.

Provides automatic fallback to alternative models when primary fails.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from flowforge_server.services.ai import AIResponse, AIService

    from . import ProviderRegistry
    from .health import HealthChecker


class FallbackExecutor:
    """
    Executes LLM calls with automatic fallback on failure.

    Features:
    - Automatic retry with alternative models
    - Health-aware model selection
    - Configurable fallback conditions
    """

    def __init__(
        self,
        ai_service: AIService,
        registry: ProviderRegistry,
        health_checker: HealthChecker | None = None,
    ) -> None:
        """
        Initialize the fallback executor.

        Args:
            ai_service: AI service for making completions
            registry: Provider registry for model resolution
            health_checker: Health checker for provider status
        """
        self.ai_service = ai_service
        self.registry = registry
        self.health_checker = health_checker

    async def complete_with_fallback(
        self,
        fallback_chain: str | list[str],
        messages: list[dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        skip_unhealthy: bool = True,
        **kwargs: Any,
    ) -> AIResponse:
        """
        Execute completion with automatic fallback.

        Args:
            fallback_chain: Name of fallback chain or list of models
            messages: Chat messages
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            skip_unhealthy: Skip models marked as unhealthy
            **kwargs: Additional completion parameters

        Returns:
            AIResponse from the first successful model

        Raises:
            Exception: If all models fail
        """
        models = self._resolve_chain(fallback_chain)

        if not models:
            raise ValueError(f"No models found in fallback chain: {fallback_chain}")

        last_error: Exception | None = None
        attempted_models: list[str] = []

        for model in models:
            # Skip unhealthy models if enabled
            if skip_unhealthy and self.health_checker:
                config = self.registry.get_model_config(model)
                if not self.health_checker.is_healthy(config.provider):
                    continue

            attempted_models.append(model)

            try:
                response = await self.ai_service.complete(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    max_retries=1,  # Don't retry within fallback
                    **kwargs,
                )

                # Mark success for health tracking
                if self.health_checker:
                    config = self.registry.get_model_config(model)
                    self.health_checker.mark_success(
                        config.provider,
                        response.usage.latency_ms,
                    )

                return response

            except Exception as e:
                last_error = e

                # Update health tracking
                if self.health_checker:
                    config = self.registry.get_model_config(model)
                    if self._is_rate_limit_error(e):
                        self.health_checker.mark_rate_limited(config.provider)
                    else:
                        self.health_checker.mark_error(config.provider, str(e))

                # Check if we should try the next model
                if not self._should_fallback(e):
                    raise

        # All models failed
        if not attempted_models:
            raise ValueError(
                f"No healthy models available in fallback chain: {fallback_chain}"
            )

        raise last_error or Exception(
            f"All models in fallback chain failed: {attempted_models}"
        )

    async def complete_stream_with_fallback(
        self,
        fallback_chain: str | list[str],
        messages: list[dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        skip_unhealthy: bool = True,
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Execute streaming completion with automatic fallback.

        Note: Fallback only happens before streaming starts. Once streaming
        begins, errors will propagate.

        Args:
            fallback_chain: Name of fallback chain or list of models
            messages: Chat messages
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            skip_unhealthy: Skip models marked as unhealthy
            **kwargs: Additional completion parameters

        Yields:
            Stream chunks from complete_stream

        Raises:
            Exception: If all models fail to start streaming
        """
        models = self._resolve_chain(fallback_chain)

        if not models:
            raise ValueError(f"No models found in fallback chain: {fallback_chain}")

        last_error: Exception | None = None
        attempted_models: list[str] = []

        for model in models:
            # Skip unhealthy models if enabled
            if skip_unhealthy and self.health_checker:
                config = self.registry.get_model_config(model)
                if not self.health_checker.is_healthy(config.provider):
                    continue

            attempted_models.append(model)

            try:
                # Try to start the stream
                stream = self.ai_service.complete_stream(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs,
                )

                # Yield all chunks from this stream
                async for chunk in stream:
                    yield chunk

                    # Mark success on completion
                    if chunk.get("type") == "done" and self.health_checker:
                        config = self.registry.get_model_config(model)
                        usage = chunk.get("usage")
                        if usage:
                            self.health_checker.mark_success(
                                config.provider,
                                usage.latency_ms,
                            )

                # Stream completed successfully
                return

            except Exception as e:
                last_error = e

                # Update health tracking
                if self.health_checker:
                    config = self.registry.get_model_config(model)
                    if self._is_rate_limit_error(e):
                        self.health_checker.mark_rate_limited(config.provider)
                    else:
                        self.health_checker.mark_error(config.provider, str(e))

                # Check if we should try the next model
                if not self._should_fallback(e):
                    raise

        # All models failed
        if not attempted_models:
            raise ValueError(
                f"No healthy models available in fallback chain: {fallback_chain}"
            )

        raise last_error or Exception(
            f"All models in fallback chain failed: {attempted_models}"
        )

    def _resolve_chain(self, chain: str | list[str]) -> list[str]:
        """Resolve fallback chain to list of models."""
        if isinstance(chain, list):
            return [self.registry.resolve_alias(m) for m in chain]

        # Look up named chain
        chain_config = self.registry.get_fallback_chain(chain)
        if chain_config:
            return [self.registry.resolve_alias(m) for m in chain_config.models]

        # Treat as single model
        return [self.registry.resolve_alias(chain)]

    def _should_fallback(self, error: Exception) -> bool:
        """Determine if we should try the next model."""
        error_str = str(error).lower()
        return any(
            x in error_str
            for x in [
                "rate",
                "quota",
                "timeout",
                "429",
                "500",
                "502",
                "503",
                "overloaded",
                "capacity",
            ]
        )

    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if error is a rate limit error."""
        error_str = str(error).lower()
        return any(x in error_str for x in ["rate", "quota", "429", "too many"])
