"""AI service for executing LLM calls."""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, TypeVar

import redis.asyncio as redis
from pydantic import BaseModel

from flowforge_server.config import get_settings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from flowforge_server.services.providers import ProviderRegistry
    from flowforge_server.services.providers.health import HealthChecker
    from flowforge_server.services.structured import StructuredOutputService

T = TypeVar("T", bound=BaseModel)


@dataclass
class ToolCall:
    """Represents a tool call from the LLM."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class AIUsage:
    """Token usage and cost tracking."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    model: str = ""
    provider: str = ""
    latency_ms: int = 0


@dataclass
class AIResponse:
    """Response from an AI call."""

    content: str
    model: str
    provider: str
    usage: AIUsage
    finish_reason: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw_response: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = {
            "content": self.content,
            "model": self.model,
            "provider": self.provider,
            "usage": {
                "prompt_tokens": self.usage.prompt_tokens,
                "completion_tokens": self.usage.completion_tokens,
                "total_tokens": self.usage.total_tokens,
                "cost_usd": self.usage.cost_usd,
                "latency_ms": self.usage.latency_ms,
            },
            "finish_reason": self.finish_reason,
        }

        if self.tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc.id,
                    "name": tc.name,
                    "arguments": tc.arguments,
                }
                for tc in self.tool_calls
            ]

        return result


# Model pricing (per 1M tokens) - updated February 2026
MODEL_PRICING = {
    # OpenAI GPT-5 Family
    "gpt-5.3": {"input": 2.00, "output": 16.00},
    "gpt-5.2": {"input": 1.75, "output": 14.00},
    # OpenAI O-Series (Reasoning)
    "o1": {"input": 15.00, "output": 60.00},
    "o3": {"input": 2.00, "output": 8.00},
    "o3-mini": {"input": 1.10, "output": 4.40},
    "o4-mini": {"input": 1.10, "output": 4.40},
    # Anthropic Claude (Latest)
    "claude-opus-4-6": {"input": 5.00, "output": 25.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5-20251001": {"input": 1.00, "output": 5.00},
    # Google Gemini 3 Series
    "gemini-3.1-pro": {"input": 1.50, "output": 12.00},
    "gemini-3-pro": {"input": 1.25, "output": 10.00},
    "gemini-3-flash": {"input": 0.30, "output": 2.50},
    # Google Gemini 2.5 Series (Budget)
    "gemini-2.5-flash": {"input": 0.15, "output": 1.25},
}


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate cost in USD for a model call."""
    # Find pricing (check for partial matches)
    pricing = None
    for model_name, price in MODEL_PRICING.items():
        if model_name in model or model in model_name:
            pricing = price
            break

    if not pricing:
        # Default pricing
        pricing = {"input": 1.00, "output": 2.00}

    input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output"]

    return round(input_cost + output_cost, 6)


def detect_provider(model: str) -> str:
    """Detect the provider from the model name."""
    model_lower = model.lower()

    if model_lower.startswith(("gpt", "o3", "o4")):
        return "openai"
    elif model_lower.startswith("claude"):
        return "anthropic"
    elif model_lower.startswith("gemini"):
        return "google"
    elif model_lower.startswith("mistral"):
        return "mistral"
    elif model_lower.startswith("llama"):
        return "meta"

    return "unknown"


class AIService:
    """
    Service for executing AI/LLM calls.

    Features:
    - Multi-provider support via LiteLLM
    - Automatic retry with exponential backoff
    - Rate limit handling
    - Cost tracking
    - Response caching
    - Structured output generation (Pydantic)
    - Provider health tracking
    """

    def __init__(
        self,
        redis_url: str | None = None,
        cache_ttl: int = 3600,  # 1 hour default cache
        provider_registry: ProviderRegistry | None = None,
        health_checker: HealthChecker | None = None,
    ) -> None:
        settings = get_settings()
        self.redis_url = redis_url or settings.redis_url
        self.cache_ttl = cache_ttl

        self._redis: redis.Redis | None = None
        self._provider_registry = provider_registry
        self._health_checker = health_checker
        self._structured_service: StructuredOutputService | None = None

    @property
    def provider_registry(self) -> ProviderRegistry | None:
        """Get the provider registry."""
        return self._provider_registry

    @provider_registry.setter
    def provider_registry(self, registry: ProviderRegistry) -> None:
        """Set the provider registry."""
        self._provider_registry = registry

    @property
    def health_checker(self) -> HealthChecker | None:
        """Get the health checker."""
        return self._health_checker

    @health_checker.setter
    def health_checker(self, checker: HealthChecker) -> None:
        """Set the health checker."""
        self._health_checker = checker

    def _get_structured_service(self) -> StructuredOutputService:
        """Get or create the structured output service."""
        if self._structured_service is None:
            from flowforge_server.services.structured import StructuredOutputService
            self._structured_service = StructuredOutputService(ai_service=self)
        return self._structured_service

    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis client for caching."""
        if self._redis is None:
            self._redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._redis

    async def close(self) -> None:
        """Close connections."""
        if self._redis:
            await self._redis.aclose()
            self._redis = None

    def _cache_key(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> str:
        """Generate a cache key for the request."""
        cache_data = {
            "model": model,
            "messages": messages,
            **{k: v for k, v in kwargs.items() if k not in ["stream"]},
        }
        content = json.dumps(cache_data, sort_keys=True)
        return f"flowforge:ai_cache:{hashlib.sha256(content.encode()).hexdigest()}"

    async def _get_cached(self, cache_key: str) -> AIResponse | None:
        """Get cached response if available."""
        try:
            client = await self._get_redis()
            cached = await client.get(cache_key)

            if cached:
                data = json.loads(cached)

                # Parse tool calls if present
                tool_calls_list = []
                if "tool_calls" in data:
                    for tc in data["tool_calls"]:
                        tool_calls_list.append(
                            ToolCall(
                                id=tc["id"],
                                name=tc["name"],
                                arguments=tc["arguments"],
                            )
                        )

                return AIResponse(
                    content=data["content"],
                    model=data["model"],
                    provider=data["provider"],
                    usage=AIUsage(
                        prompt_tokens=data["usage"]["prompt_tokens"],
                        completion_tokens=data["usage"]["completion_tokens"],
                        total_tokens=data["usage"]["total_tokens"],
                        cost_usd=data["usage"]["cost_usd"],
                        latency_ms=0,  # Cached response has no latency
                        model=data["model"],
                        provider=data["provider"],
                    ),
                    finish_reason=data.get("finish_reason"),
                    tool_calls=tool_calls_list,
                )
        except Exception:
            pass

        return None

    async def _set_cached(
        self,
        cache_key: str,
        response: AIResponse,
        ttl: int | None = None,
    ) -> None:
        """Cache a response."""
        try:
            client = await self._get_redis()
            data = response.to_dict()
            await client.set(
                cache_key,
                json.dumps(data),
                ex=ttl or self.cache_ttl,
            )
        except Exception:
            pass

    async def complete(
        self,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        max_retries: int = 3,
        use_cache: bool = True,
        cache_ttl: int | None = None,
        tools: list[Any] | None = None,
        tool_choice: str | dict[str, Any] = "auto",
        response_model: type[T] | None = None,
        tenant_id: uuid.UUID | None = None,
        session: AsyncSession | None = None,
        **kwargs: Any,
    ) -> AIResponse | T:
        """
        Generate a completion from an AI model.

        Args:
            model: Model identifier (e.g., "gpt-5.3", "claude-sonnet-4-6").
            messages: List of message dicts with 'role' and 'content'.
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.
            max_retries: Maximum retry attempts.
            use_cache: Whether to use caching.
            cache_ttl: Cache TTL in seconds (overrides default).
            tools: List of Tool objects that can be called.
            tool_choice: How the LLM should choose tools ("auto", "required", "none", or specific tool).
            response_model: Optional Pydantic model for structured output generation.
            tenant_id: Optional tenant ID for per-tenant API key lookup.
            session: Optional database session for tenant key lookup.
            **kwargs: Additional provider-specific parameters.

        Returns:
            AIResponse with content and usage information, or a Pydantic model instance
            if response_model is provided.
        """
        # Handle structured output generation
        if response_model is not None:
            structured_service = self._get_structured_service()
            return await structured_service.generate(
                model=model,
                response_model=response_model,
                messages=messages,
                max_retries=max_retries,
                temperature=temperature,
                **kwargs,
            )
        # Check cache
        cache_key = None
        if use_cache:
            cache_key = self._cache_key(
                model, messages, max_tokens=max_tokens, tools=tools, tool_choice=tool_choice, **kwargs
            )
            cached = await self._get_cached(cache_key)
            if cached:
                return cached

        provider = detect_provider(model)
        start_time = time.time()

        # Convert tools to provider-specific format if provided
        tool_schemas = None
        if tools:
            tool_schemas = []
            for tool in tools:
                # Check if it's a Tool object from the SDK
                tool_type_name = type(tool).__name__
                if tool_type_name == "Tool" and hasattr(tool, "to_anthropic_schema"):
                    # Detect provider and use appropriate schema
                    if provider == "anthropic":
                        tool_schemas.append(tool.to_anthropic_schema())
                    else:
                        # Default to OpenAI format (also works for most providers via LiteLLM)
                        tool_schemas.append(tool.to_openai_schema())
                else:
                    # Assume it's already a schema dict
                    tool_schemas.append(tool)

        # Try to import litellm
        try:
            import litellm
            litellm.drop_params = True  # Ignore unsupported params
        except ImportError:
            raise ImportError(
                "litellm package required for AI service. "
                "Install with: pip install litellm"
            )

        # Add provider prefix for litellm routing if needed
        litellm_model = model
        if model.startswith("claude") and not model.startswith("anthropic/"):
            litellm_model = f"anthropic/{model}"

        # Set up tenant-specific credential if provided
        credential_override: str | None = None
        credential_auth_type: str = "api_key"
        if tenant_id and session and self._provider_registry:
            try:
                result = await self._provider_registry.get_api_key_for_tenant(
                    session, tenant_id, provider
                )
                if result:
                    credential_override, credential_auth_type = result
            except Exception:
                # Fall back to default behavior if lookup fails
                pass

        # Retry loop
        last_error = None
        for attempt in range(max_retries):
            try:
                # Build completion params
                completion_params = {
                    "model": litellm_model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    **kwargs,
                }

                # Add credential override
                if credential_override:
                    completion_params["api_key"] = credential_override

                # Add tools if provided
                if tool_schemas:
                    if provider == "anthropic":
                        completion_params["tools"] = tool_schemas
                    else:
                        completion_params["tools"] = tool_schemas

                    # Add tool_choice if specified
                    if tool_choice != "auto":
                        completion_params["tool_choice"] = tool_choice

                response = await litellm.acompletion(**completion_params)

                latency_ms = int((time.time() - start_time) * 1000)

                # Extract usage
                prompt_tokens = response.usage.prompt_tokens if response.usage else 0
                completion_tokens = response.usage.completion_tokens if response.usage else 0
                total_tokens = response.usage.total_tokens if response.usage else 0

                # Calculate cost (use provider registry if available)
                if self._provider_registry and session and tenant_id:
                    # Use async pricing with tenant-specific/global custom pricing
                    cost = await self._provider_registry.calculate_cost_async(
                        session, tenant_id, model, prompt_tokens, completion_tokens
                    )
                elif self._provider_registry:
                    # Fallback to sync pricing (defaults only)
                    cost = self._provider_registry.calculate_cost(
                        model, prompt_tokens, completion_tokens
                    )
                else:
                    cost = calculate_cost(model, prompt_tokens, completion_tokens)

                # Track health
                if self._health_checker:
                    self._health_checker.mark_success(provider, latency_ms)

                usage = AIUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    cost_usd=cost,
                    model=model,
                    provider=provider,
                    latency_ms=latency_ms,
                )

                # Parse tool calls if present
                tool_calls_list = []
                message = response.choices[0].message
                if hasattr(message, "tool_calls") and message.tool_calls:
                    for tc in message.tool_calls:
                        # Parse arguments (may be string or dict)
                        args = tc.function.arguments
                        if isinstance(args, str):
                            import json
                            args = json.loads(args)

                        tool_calls_list.append(
                            ToolCall(
                                id=tc.id,
                                name=tc.function.name,
                                arguments=args,
                            )
                        )

                result = AIResponse(
                    content=message.content or "",
                    model=response.model or model,
                    provider=provider,
                    usage=usage,
                    finish_reason=response.choices[0].finish_reason,
                    tool_calls=tool_calls_list,
                    raw_response=response.model_dump() if hasattr(response, "model_dump") else {},
                )

                # Cache successful response
                if use_cache and cache_key:
                    await self._set_cached(cache_key, result, cache_ttl)

                return result

            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                # Check if rate limited
                is_rate_limit = (
                    "rate" in error_str
                    or "quota" in error_str
                    or "429" in error_str
                    or "too many" in error_str
                )

                # Track health on errors
                if self._health_checker:
                    if is_rate_limit:
                        self._health_checker.mark_rate_limited(provider)
                    else:
                        self._health_checker.mark_error(provider, str(e))

                if is_rate_limit and attempt < max_retries - 1:
                    # Exponential backoff for rate limits
                    wait_time = min(2 ** (attempt + 1), 60)
                    await asyncio.sleep(wait_time)
                    continue

                # Check if retryable
                is_retryable = (
                    is_rate_limit
                    or "timeout" in error_str
                    or "connection" in error_str
                    or "500" in error_str
                    or "502" in error_str
                    or "503" in error_str
                )

                if is_retryable and attempt < max_retries - 1:
                    # Short backoff for other retryable errors
                    await asyncio.sleep(1 * (attempt + 1))
                    continue

                # Non-retryable or max retries exceeded
                break

        # All retries failed
        raise last_error or Exception("AI completion failed")

    async def complete_stream(
        self,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        tools: list[Any] | None = None,
        tool_choice: str | dict[str, Any] = "auto",
        tenant_id: uuid.UUID | None = None,
        session: AsyncSession | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Stream a completion from an AI model token by token.

        Args:
            model: Model identifier (e.g., "gpt-5.3", "claude-sonnet-4-6").
            messages: List of message dicts with 'role' and 'content'.
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.
            tools: List of Tool objects that can be called.
            tool_choice: How the LLM should choose tools.
            **kwargs: Additional provider-specific parameters.

        Yields:
            Dict with either:
            - {"type": "content", "chunk": str} for content chunks
            - {"type": "tool_call", "tool_call": ToolCall} for tool calls
            - {"type": "done", "usage": AIUsage, "finish_reason": str} when complete
        """
        provider = detect_provider(model)
        start_time = time.time()

        # Convert tools to provider-specific format if provided
        tool_schemas = None
        if tools:
            tool_schemas = []
            for tool in tools:
                tool_type_name = type(tool).__name__
                if tool_type_name == "Tool" and hasattr(tool, "to_anthropic_schema"):
                    if provider == "anthropic":
                        tool_schemas.append(tool.to_anthropic_schema())
                    else:
                        tool_schemas.append(tool.to_openai_schema())
                else:
                    tool_schemas.append(tool)

        # Try to import litellm
        try:
            import litellm
            litellm.drop_params = True
        except ImportError:
            raise ImportError(
                "litellm package required for AI service. "
                "Install with: pip install litellm"
            )

        # Add provider prefix for litellm routing if needed
        litellm_model = model
        if model.startswith("claude") and not model.startswith("anthropic/"):
            litellm_model = f"anthropic/{model}"

        # Build completion params with streaming enabled
        completion_params = {
            "model": litellm_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
            "stream_options": {"include_usage": True},
            **kwargs,
        }

        # Set up tenant-specific credential if provided
        credential_override: str | None = None
        if tenant_id and session and self._provider_registry:
            try:
                result = await self._provider_registry.get_api_key_for_tenant(
                    session, tenant_id, provider
                )
                if result:
                    credential_override, _ = result
            except Exception:
                pass

        if credential_override:
            completion_params["api_key"] = credential_override

        if tool_schemas:
            completion_params["tools"] = tool_schemas
            if tool_choice != "auto":
                completion_params["tool_choice"] = tool_choice

        response = await litellm.acompletion(**completion_params)

        # Track accumulated data
        accumulated_content = ""
        accumulated_tool_calls: dict[int, dict] = {}  # index -> partial tool call
        prompt_tokens = 0
        completion_tokens = 0

        async for chunk in response:
            choice = chunk.choices[0] if chunk.choices else None
            if not choice:
                continue

            delta = choice.delta

            # Handle content chunks
            if delta.content:
                accumulated_content += delta.content
                yield {"type": "content", "chunk": delta.content}

            # Handle tool call chunks (streaming tool calls come in pieces)
            if hasattr(delta, "tool_calls") and delta.tool_calls:
                for tc_chunk in delta.tool_calls:
                    idx = tc_chunk.index
                    if idx not in accumulated_tool_calls:
                        accumulated_tool_calls[idx] = {
                            "id": "",
                            "name": "",
                            "arguments": "",
                        }

                    if tc_chunk.id:
                        accumulated_tool_calls[idx]["id"] = tc_chunk.id
                    if tc_chunk.function:
                        if tc_chunk.function.name:
                            accumulated_tool_calls[idx]["name"] = tc_chunk.function.name
                        if tc_chunk.function.arguments:
                            accumulated_tool_calls[idx]["arguments"] += tc_chunk.function.arguments

            # Check for finish reason
            if choice.finish_reason:
                latency_ms = int((time.time() - start_time) * 1000)

                # Try to get usage from final chunk
                if hasattr(chunk, "usage") and chunk.usage:
                    prompt_tokens = chunk.usage.prompt_tokens or 0
                    completion_tokens = chunk.usage.completion_tokens or 0

                # Fallback: estimate tokens if usage not available from stream
                if prompt_tokens == 0 and completion_tokens == 0:
                    try:
                        prompt_tokens = litellm.token_counter(model=model, messages=messages)
                        completion_tokens = litellm.token_counter(model=model, text=accumulated_content)
                    except Exception:
                        pass

                # Parse accumulated tool calls
                tool_calls_list = []
                for idx in sorted(accumulated_tool_calls.keys()):
                    tc_data = accumulated_tool_calls[idx]
                    try:
                        args = json.loads(tc_data["arguments"]) if tc_data["arguments"] else {}
                    except json.JSONDecodeError:
                        args = {}

                    tool_call = ToolCall(
                        id=tc_data["id"],
                        name=tc_data["name"],
                        arguments=args,
                    )
                    tool_calls_list.append(tool_call)
                    yield {"type": "tool_call", "tool_call": tool_call}

                # Calculate cost (use provider registry if available)
                if self._provider_registry:
                    cost = self._provider_registry.calculate_cost(
                        model, prompt_tokens, completion_tokens
                    )
                else:
                    cost = calculate_cost(model, prompt_tokens, completion_tokens)

                # Track health
                if self._health_checker:
                    self._health_checker.mark_success(provider, latency_ms)

                usage = AIUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                    cost_usd=cost,
                    model=model,
                    provider=provider,
                    latency_ms=latency_ms,
                )

                yield {
                    "type": "done",
                    "content": accumulated_content,
                    "usage": usage,
                    "finish_reason": choice.finish_reason,
                    "tool_calls": tool_calls_list,
                }
                break

    async def get_usage_stats(
        self,
        tenant_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Get usage statistics for a tenant.

        TODO: Implement usage tracking in database.
        """
        return {
            "tenant_id": tenant_id,
            "total_requests": 0,
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "by_model": {},
        }


# Global service instance
_ai_service: AIService | None = None


def get_ai_service() -> AIService:
    """Get the global AI service instance."""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
