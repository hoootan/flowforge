"""Provider configuration models.

Defines Pydantic models for provider settings, model configurations,
and fallback chain definitions.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class ProviderSettings(BaseModel):
    """Settings for a specific AI provider."""

    api_key: str | None = None
    api_base: str | None = None

    # Rate limiting
    requests_per_minute: int | None = None
    tokens_per_minute: int | None = None

    # Timeouts
    timeout_seconds: float = 60.0
    connect_timeout_seconds: float = 10.0

    # Retry settings
    max_retries: int = 3
    retry_delay_seconds: float = 1.0

    # Provider-specific options
    extra: dict[str, Any] = Field(default_factory=dict)


class ModelConfig(BaseModel):
    """Configuration for a specific model."""

    provider: str  # openai, anthropic, google, etc.
    model_id: str  # The actual model identifier

    # Override provider settings for this model
    settings: ProviderSettings | None = None

    # Pricing (per 1M tokens)
    input_price_per_m: float | None = None
    output_price_per_m: float | None = None

    # Capabilities
    supports_tools: bool = True
    supports_vision: bool = False
    supports_streaming: bool = True
    max_output_tokens: int = 4096
    context_window: int = 128000


class FallbackConfig(BaseModel):
    """Configuration for a fallback chain."""

    name: str
    models: list[str]  # Model aliases in order of preference
    conditions: list[Literal["rate_limit", "timeout", "error", "all"]] = Field(
        default_factory=lambda: ["all"]
    )


# Default model configurations with pricing (updated February 2026)
DEFAULT_MODEL_CONFIGS: dict[str, ModelConfig] = {
    # ===================
    # OpenAI GPT-5 Family (Latest)
    # ===================
    "gpt-5.2": ModelConfig(
        provider="openai",
        model_id="gpt-5.2",
        input_price_per_m=1.75,
        output_price_per_m=14.00,
        supports_vision=True,
        context_window=400000,
    ),
    "gpt-5.1": ModelConfig(
        provider="openai",
        model_id="gpt-5.1",
        input_price_per_m=1.25,
        output_price_per_m=10.00,
        supports_vision=True,
        context_window=400000,
    ),
    "gpt-5": ModelConfig(
        provider="openai",
        model_id="gpt-5",
        input_price_per_m=1.25,
        output_price_per_m=10.00,
        supports_vision=True,
        context_window=400000,
    ),
    "gpt-5-mini": ModelConfig(
        provider="openai",
        model_id="gpt-5-mini",
        input_price_per_m=0.25,
        output_price_per_m=2.00,
        supports_vision=True,
        context_window=400000,
    ),
    "gpt-5-nano": ModelConfig(
        provider="openai",
        model_id="gpt-5-nano",
        input_price_per_m=0.05,
        output_price_per_m=0.40,
        supports_vision=True,
        context_window=200000,
    ),
    # ===================
    # OpenAI GPT-4.1 Family
    # ===================
    "gpt-4.1": ModelConfig(
        provider="openai",
        model_id="gpt-4.1",
        input_price_per_m=2.00,
        output_price_per_m=8.00,
        supports_vision=True,
        context_window=1000000,
    ),
    "gpt-4.1-mini": ModelConfig(
        provider="openai",
        model_id="gpt-4.1-mini",
        input_price_per_m=0.40,
        output_price_per_m=1.60,
        supports_vision=True,
        context_window=1000000,
    ),
    # ===================
    # OpenAI O-Series (Reasoning Models)
    # ===================
    "o1": ModelConfig(
        provider="openai",
        model_id="o1",
        input_price_per_m=15.00,
        output_price_per_m=60.00,
        supports_tools=True,
        supports_streaming=False,
        context_window=200000,
    ),
    "o3": ModelConfig(
        provider="openai",
        model_id="o3",
        input_price_per_m=2.00,
        output_price_per_m=8.00,
        supports_tools=True,
        supports_streaming=False,
        context_window=200000,
    ),
    "o3-mini": ModelConfig(
        provider="openai",
        model_id="o3-mini",
        input_price_per_m=1.10,
        output_price_per_m=4.40,
        supports_tools=True,
        supports_streaming=False,
        context_window=200000,
    ),
    "o4-mini": ModelConfig(
        provider="openai",
        model_id="o4-mini",
        input_price_per_m=1.10,
        output_price_per_m=4.40,
        supports_tools=True,
        supports_streaming=False,
        context_window=200000,
    ),
    # ===================
    # Anthropic Claude 4.6 Series (Latest)
    # ===================
    "claude-opus-4-6": ModelConfig(
        provider="anthropic",
        model_id="claude-opus-4-6",
        input_price_per_m=5.00,
        output_price_per_m=25.00,
        supports_vision=True,
        context_window=200000,
        max_output_tokens=128000,
    ),
    "claude-sonnet-4-6": ModelConfig(
        provider="anthropic",
        model_id="claude-sonnet-4-6",
        input_price_per_m=3.00,
        output_price_per_m=15.00,
        supports_vision=True,
        context_window=200000,
        max_output_tokens=64000,
    ),
    "claude-haiku-4-5-20251001": ModelConfig(
        provider="anthropic",
        model_id="claude-haiku-4-5-20251001",
        input_price_per_m=1.00,
        output_price_per_m=5.00,
        supports_vision=True,
        context_window=200000,
        max_output_tokens=64000,
    ),
    # ===================
    # Google Gemini 2.5 Series (Latest)
    # ===================
    "gemini-2.5-pro": ModelConfig(
        provider="google",
        model_id="gemini-2.5-pro",
        input_price_per_m=1.25,
        output_price_per_m=10.00,
        supports_vision=True,
        context_window=1000000,
    ),
    "gemini-2.5-flash": ModelConfig(
        provider="google",
        model_id="gemini-2.5-flash",
        input_price_per_m=0.30,
        output_price_per_m=2.50,
        supports_vision=True,
        context_window=1000000,
    ),
    "gemini-2.5-flash-lite": ModelConfig(
        provider="google",
        model_id="gemini-2.5-flash-lite",
        input_price_per_m=0.10,
        output_price_per_m=0.40,
        supports_vision=True,
        context_window=1000000,
    ),
    # ===================
    # Google Gemini 2.0 Series
    # ===================
    "gemini-2.0-flash": ModelConfig(
        provider="google",
        model_id="gemini-2.0-flash",
        input_price_per_m=0.10,
        output_price_per_m=0.40,
        supports_vision=True,
        context_window=1000000,
    ),
    "gemini-2.0-flash-lite": ModelConfig(
        provider="google",
        model_id="gemini-2.0-flash-lite",
        input_price_per_m=0.075,
        output_price_per_m=0.30,
        supports_vision=True,
        context_window=1000000,
    ),
}

# Model aliases for convenience
MODEL_ALIASES: dict[str, str] = {
    # OpenAI GPT aliases
    "gpt-5-latest": "gpt-5.2",
    "gpt-5-fast": "gpt-5-mini",
    "gpt-5-cheap": "gpt-5-nano",
    "gpt-4-latest": "gpt-4.1",
    "gpt-4-fast": "gpt-4.1-mini",
    # OpenAI O-series aliases
    "o3-latest": "o3",
    "o-fast": "o4-mini",
    "o-latest": "o4-mini",
    # Anthropic Claude aliases
    "claude": "claude-sonnet-4-6",
    "claude-sonnet": "claude-sonnet-4-6",
    "claude-sonnet-4.6": "claude-sonnet-4-6",
    "claude-opus": "claude-opus-4-6",
    "claude-opus-4.6": "claude-opus-4-6",
    "claude-haiku": "claude-haiku-4-5-20251001",
    "claude-haiku-4.5": "claude-haiku-4-5-20251001",
    # Google Gemini aliases
    "gemini": "gemini-2.5-pro",
    "gemini-latest": "gemini-2.5-pro",
    "gemini-flash": "gemini-2.5-flash",
    "gemini-flash-lite": "gemini-2.5-flash-lite",
    # Use case aliases
    "fast": "gpt-5-mini",
    "fastest": "gpt-5-nano",
    "smart": "claude-opus-4-6",
    "smartest": "claude-opus-4-6",
    "coding": "claude-sonnet-4-6",
    "cheap": "gemini-2.0-flash",
    "cheapest": "gpt-5-nano",
    "reasoning": "o3",
    "reasoning-fast": "o4-mini",
    "reasoning-deep": "o1",
}

# Default fallback chains
DEFAULT_FALLBACK_CHAINS: dict[str, FallbackConfig] = {
    "default": FallbackConfig(
        name="default",
        models=["gpt-5", "claude-sonnet-4-6", "gemini-2.5-pro"],
    ),
    "fast": FallbackConfig(
        name="fast",
        models=["gpt-5-mini", "claude-haiku-4-5-20251001", "gemini-2.5-flash"],
    ),
    "smart": FallbackConfig(
        name="smart",
        models=["claude-opus-4-6", "gpt-5.2", "gemini-2.5-pro"],
    ),
    "cheap": FallbackConfig(
        name="cheap",
        models=["gpt-5-nano", "gemini-2.0-flash", "gemini-2.0-flash-lite"],
    ),
    "reasoning": FallbackConfig(
        name="reasoning",
        models=["o3", "o4-mini", "o3-mini"],
    ),
    "coding": FallbackConfig(
        name="coding",
        models=["claude-sonnet-4-6", "claude-opus-4-6", "gpt-4.1"],
    ),
}


class ProviderRegistryConfig(BaseModel):
    """Complete provider configuration."""

    # Provider-level settings
    providers: dict[str, ProviderSettings] = Field(default_factory=dict)

    # Model configurations (overrides defaults)
    models: dict[str, ModelConfig] = Field(default_factory=dict)

    # Model aliases (overrides defaults)
    aliases: dict[str, str] = Field(default_factory=dict)

    # Fallback chains (overrides defaults)
    fallbacks: dict[str, FallbackConfig] = Field(default_factory=dict)

    # Default model for various use cases
    defaults: dict[str, str] = Field(
        default_factory=lambda: {
            "default": "gpt-5",
            "fast": "gpt-5-mini",
            "smart": "claude-opus-4-6",
            "coding": "claude-sonnet-4-6",
            "cheap": "gpt-5-nano",
            "reasoning": "o3",
        }
    )
