"""AI provider implementations for FlowForge."""

from abc import ABC, abstractmethod
from typing import Any
import json


class AIProvider(ABC):
    """Base class for AI providers."""

    @abstractmethod
    async def complete(
        self,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Generate a completion from the AI model.

        Args:
            model: Model identifier.
            messages: List of message dicts with 'role' and 'content'.
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.
            **kwargs: Additional provider-specific parameters.

        Returns:
            Dict with 'content', 'model', 'usage', and provider-specific data.
        """
        pass


class OpenAIProvider(AIProvider):
    """OpenAI API provider."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key

    async def complete(
        self,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> dict[str, Any]:
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError("openai package required. Install with: pip install openai")

        client = AsyncOpenAI(api_key=self.api_key)

        response = await client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )

        return {
            "content": response.choices[0].message.content,
            "model": response.model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
            "finish_reason": response.choices[0].finish_reason,
        }


class AnthropicProvider(AIProvider):
    """Anthropic API provider."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key

    async def complete(
        self,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> dict[str, Any]:
        try:
            from anthropic import AsyncAnthropic
        except ImportError:
            raise ImportError("anthropic package required. Install with: pip install anthropic")

        client = AsyncAnthropic(api_key=self.api_key)

        # Extract system message if present
        system = None
        filtered_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                filtered_messages.append(msg)

        response = await client.messages.create(
            model=model,
            messages=filtered_messages,  # type: ignore
            max_tokens=max_tokens,
            system=system or "",
            **kwargs,
        )

        return {
            "content": response.content[0].text if response.content else "",
            "model": response.model,
            "usage": {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            },
            "stop_reason": response.stop_reason,
        }


class LiteLLMProvider(AIProvider):
    """
    LiteLLM provider for unified access to multiple AI providers.

    Supports OpenAI, Anthropic, Cohere, Hugging Face, and many more
    through a unified interface.
    """

    def __init__(self) -> None:
        pass

    async def complete(
        self,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> dict[str, Any]:
        try:
            import litellm
        except ImportError:
            raise ImportError("litellm package required. Install with: pip install litellm")

        response = await litellm.acompletion(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )

        return {
            "content": response.choices[0].message.content,
            "model": response.model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
            "finish_reason": response.choices[0].finish_reason,
        }


def get_provider(provider_name: str | None = None, model: str | None = None) -> AIProvider:
    """
    Get an AI provider instance.

    Args:
        provider_name: Explicit provider name ('openai', 'anthropic', 'litellm').
        model: Model name to auto-detect provider from.

    Returns:
        AIProvider instance.
    """
    if provider_name:
        provider_name = provider_name.lower()
        if provider_name == "openai":
            return OpenAIProvider()
        elif provider_name == "anthropic":
            return AnthropicProvider()
        elif provider_name == "litellm":
            return LiteLLMProvider()
        else:
            # Default to LiteLLM for unknown providers
            return LiteLLMProvider()

    # Auto-detect from model name
    if model:
        model_lower = model.lower()
        if model_lower.startswith("gpt") or model_lower.startswith("o1"):
            return OpenAIProvider()
        elif model_lower.startswith("claude"):
            return AnthropicProvider()

    # Default to LiteLLM
    return LiteLLMProvider()
