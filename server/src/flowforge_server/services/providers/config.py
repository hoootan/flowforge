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


# Default model configurations with pricing (updated January 2026)
DEFAULT_MODEL_CONFIGS: dict[str, ModelConfig] = {
    # ===================
    # OpenAI GPT-5 Family (Latest - August 2025)
    # ===================
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
    "gpt-5-pro": ModelConfig(
        provider="openai",
        model_id="gpt-5-pro",
        input_price_per_m=15.00,
        output_price_per_m=120.00,
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
    "gpt-5.2": ModelConfig(
        provider="openai",
        model_id="gpt-5.2",
        input_price_per_m=1.25,
        output_price_per_m=10.00,
        supports_vision=True,
        context_window=400000,
    ),
    # ===================
    # OpenAI GPT-4.1 Family (April 2025)
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
    "gpt-4.1-nano": ModelConfig(
        provider="openai",
        model_id="gpt-4.1-nano",
        input_price_per_m=0.10,
        output_price_per_m=0.40,
        supports_vision=True,
        context_window=1000000,
    ),
    # ===================
    # OpenAI GPT-4o Family (Legacy)
    # ===================
    "gpt-4o": ModelConfig(
        provider="openai",
        model_id="gpt-4o",
        input_price_per_m=2.50,
        output_price_per_m=10.00,
        supports_vision=True,
        context_window=128000,
    ),
    "gpt-4o-mini": ModelConfig(
        provider="openai",
        model_id="gpt-4o-mini",
        input_price_per_m=0.15,
        output_price_per_m=0.60,
        supports_vision=True,
        context_window=128000,
    ),
    "gpt-4-turbo": ModelConfig(
        provider="openai",
        model_id="gpt-4-turbo",
        input_price_per_m=10.00,
        output_price_per_m=30.00,
        supports_vision=True,
        context_window=128000,
    ),
    # ===================
    # OpenAI O-Series (Reasoning Models)
    # ===================
    "o1": ModelConfig(
        provider="openai",
        model_id="o1",
        input_price_per_m=15.00,
        output_price_per_m=60.00,
        supports_tools=False,
        supports_streaming=False,
        context_window=200000,
    ),
    "o1-mini": ModelConfig(
        provider="openai",
        model_id="o1-mini",
        input_price_per_m=3.00,
        output_price_per_m=12.00,
        supports_tools=False,
        supports_streaming=False,
        context_window=128000,
    ),
    "o3": ModelConfig(
        provider="openai",
        model_id="o3",
        input_price_per_m=0.40,
        output_price_per_m=1.60,
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
    # Anthropic Claude 4.5 Series (Latest)
    # ===================
    "claude-opus-4-5-20250514": ModelConfig(
        provider="anthropic",
        model_id="claude-opus-4-5-20250514",
        input_price_per_m=5.00,
        output_price_per_m=25.00,
        supports_vision=True,
        context_window=200000,
    ),
    "claude-sonnet-4-5-20250514": ModelConfig(
        provider="anthropic",
        model_id="claude-sonnet-4-5-20250514",
        input_price_per_m=3.00,
        output_price_per_m=15.00,
        supports_vision=True,
        context_window=200000,
    ),
    "claude-haiku-4-5-20250514": ModelConfig(
        provider="anthropic",
        model_id="claude-haiku-4-5-20250514",
        input_price_per_m=1.00,
        output_price_per_m=5.00,
        supports_vision=True,
        context_window=200000,
    ),
    # ===================
    # Anthropic Claude 4 Series
    # ===================
    "claude-sonnet-4-20250514": ModelConfig(
        provider="anthropic",
        model_id="claude-sonnet-4-20250514",
        input_price_per_m=3.00,
        output_price_per_m=15.00,
        supports_vision=True,
        context_window=200000,
    ),
    # ===================
    # Anthropic Claude 3.x Series (Legacy)
    # ===================
    "claude-3-5-sonnet-20241022": ModelConfig(
        provider="anthropic",
        model_id="claude-3-5-sonnet-20241022",
        input_price_per_m=3.00,
        output_price_per_m=15.00,
        supports_vision=True,
        context_window=200000,
    ),
    "claude-3-opus-20240229": ModelConfig(
        provider="anthropic",
        model_id="claude-3-opus-20240229",
        input_price_per_m=15.00,
        output_price_per_m=75.00,
        supports_vision=True,
        context_window=200000,
    ),
    "claude-3-haiku-20240307": ModelConfig(
        provider="anthropic",
        model_id="claude-3-haiku-20240307",
        input_price_per_m=0.25,
        output_price_per_m=1.25,
        supports_vision=True,
        context_window=200000,
    ),
    # ===================
    # Google Gemini 3 Series (Latest - Preview)
    # ===================
    "gemini-3-pro": ModelConfig(
        provider="google",
        model_id="gemini-3-pro",
        input_price_per_m=2.00,
        output_price_per_m=12.00,
        supports_vision=True,
        context_window=1000000,
    ),
    # ===================
    # Google Gemini 2.5 Series
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
        input_price_per_m=0.10,
        output_price_per_m=0.40,
        supports_vision=True,
        context_window=1000000,
    ),
    # ===================
    # Google Gemini 1.5 Series (Legacy)
    # ===================
    "gemini-1.5-pro": ModelConfig(
        provider="google",
        model_id="gemini-1.5-pro",
        input_price_per_m=1.25,
        output_price_per_m=5.00,
        supports_vision=True,
        context_window=2000000,
    ),
    "gemini-1.5-flash": ModelConfig(
        provider="google",
        model_id="gemini-1.5-flash",
        input_price_per_m=0.075,
        output_price_per_m=0.30,
        supports_vision=True,
        context_window=1000000,
    ),
    "gemini-pro": ModelConfig(
        provider="google",
        model_id="gemini-pro",
        input_price_per_m=0.50,
        output_price_per_m=1.50,
        context_window=32000,
    ),
}

# Model aliases for convenience
MODEL_ALIASES: dict[str, str] = {
    # OpenAI GPT aliases
    "gpt-5-latest": "gpt-5.2",
    "gpt-5-fast": "gpt-5-mini",
    "gpt-5-cheap": "gpt-5-nano",
    "gpt-4": "gpt-4o",
    "gpt-4-latest": "gpt-4.1",
    "gpt-4-fast": "gpt-4.1-mini",
    "gpt-4-cheap": "gpt-4.1-nano",
    # OpenAI O-series aliases
    "o3-latest": "o3",
    "o-fast": "o3-mini",
    "o-latest": "o4-mini",
    # Anthropic Claude aliases
    "claude": "claude-sonnet-4-5-20250514",
    "claude-3-sonnet": "claude-3-5-sonnet-20241022",
    "claude-sonnet": "claude-sonnet-4-5-20250514",
    "claude-sonnet-4": "claude-sonnet-4-20250514",
    "claude-sonnet-4.5": "claude-sonnet-4-5-20250514",
    "claude-opus": "claude-opus-4-5-20250514",
    "claude-opus-4.5": "claude-opus-4-5-20250514",
    "claude-haiku": "claude-haiku-4-5-20250514",
    "claude-haiku-4.5": "claude-haiku-4-5-20250514",
    "claude-3-haiku": "claude-3-haiku-20240307",
    # Google Gemini aliases
    "gemini": "gemini-3-pro",
    "gemini-latest": "gemini-3-pro",
    "gemini-pro": "gemini-2.5-pro",
    "gemini-flash": "gemini-2.5-flash",
    "gemini-flash-lite": "gemini-2.0-flash-lite",
    "gemini-1.5": "gemini-1.5-pro",
    # Use case aliases
    "fast": "gpt-5-mini",
    "fastest": "gpt-5-nano",
    "smart": "gpt-5.2",
    "smartest": "gpt-5-pro",
    "coding": "claude-sonnet-4-5-20250514",
    "cheap": "gemini-2.0-flash",
    "cheapest": "gpt-5-nano",
    "reasoning": "o3",
    "reasoning-fast": "o3-mini",
    "reasoning-deep": "o1",
}

# Default fallback chains
DEFAULT_FALLBACK_CHAINS: dict[str, FallbackConfig] = {
    "default": FallbackConfig(
        name="default",
        models=["gpt-5", "claude-sonnet-4-5-20250514", "gemini-3-pro"],
    ),
    "fast": FallbackConfig(
        name="fast",
        models=["gpt-5-mini", "claude-haiku-4-5-20250514", "gemini-2.5-flash"],
    ),
    "smart": FallbackConfig(
        name="smart",
        models=["gpt-5.2", "claude-opus-4-5-20250514", "gemini-3-pro"],
    ),
    "cheap": FallbackConfig(
        name="cheap",
        models=["gpt-5-nano", "gemini-2.0-flash", "gpt-4.1-nano"],
    ),
    "reasoning": FallbackConfig(
        name="reasoning",
        models=["o3", "o4-mini", "o1"],
    ),
    "coding": FallbackConfig(
        name="coding",
        models=["claude-sonnet-4-5-20250514", "gpt-5.2", "gpt-4.1"],
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
            "smart": "gpt-5.2",
            "coding": "claude-sonnet-4-5-20250514",
            "cheap": "gpt-5-nano",
            "reasoning": "o3",
        }
    )
