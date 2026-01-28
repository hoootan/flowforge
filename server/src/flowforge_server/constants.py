"""Constants and enumerations for FlowForge.

This module centralizes configuration constants, model definitions,
and pricing information used across the application.
"""

from enum import Enum
from typing import TypedDict


class AIModel(str, Enum):
    """Supported AI models."""

    # OpenAI models
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_4 = "gpt-4"
    GPT_35_TURBO = "gpt-3.5-turbo"

    # Anthropic models
    CLAUDE_3_OPUS = "claude-3-opus-20240229"
    CLAUDE_3_SONNET = "claude-3-sonnet-20240229"
    CLAUDE_3_HAIKU = "claude-3-haiku-20240307"
    CLAUDE_35_SONNET = "claude-3-5-sonnet-20241022"
    CLAUDE_SONNET_4 = "claude-sonnet-4-20250514"
    CLAUDE_SONNET_4_5 = "claude-sonnet-4-5-20250514"
    CLAUDE_OPUS_4 = "claude-opus-4-20250514"
    CLAUDE_OPUS_4_5 = "claude-opus-4-5-20250514"

    # Google models
    GEMINI_15_PRO = "gemini-1.5-pro"
    GEMINI_15_FLASH = "gemini-1.5-flash"
    GEMINI_20_PRO = "gemini-2.0-pro"

    # Mistral models
    MISTRAL_LARGE = "mistral-large-latest"
    MISTRAL_MEDIUM = "mistral-medium-latest"
    MISTRAL_SMALL = "mistral-small-latest"


class ModelPricing(TypedDict):
    """Pricing structure for a model (per 1M tokens)."""

    input: float
    output: float


# Model pricing (per 1M tokens) - approximate as of early 2025
MODEL_PRICING: dict[str, ModelPricing] = {
    # OpenAI
    AIModel.GPT_4O: {"input": 2.50, "output": 10.00},
    AIModel.GPT_4O_MINI: {"input": 0.15, "output": 0.60},
    AIModel.GPT_4_TURBO: {"input": 10.00, "output": 30.00},
    AIModel.GPT_4: {"input": 30.00, "output": 60.00},
    AIModel.GPT_35_TURBO: {"input": 0.50, "output": 1.50},
    # Anthropic
    AIModel.CLAUDE_3_OPUS: {"input": 15.00, "output": 75.00},
    AIModel.CLAUDE_3_SONNET: {"input": 3.00, "output": 15.00},
    AIModel.CLAUDE_3_HAIKU: {"input": 0.25, "output": 1.25},
    AIModel.CLAUDE_35_SONNET: {"input": 3.00, "output": 15.00},
    AIModel.CLAUDE_SONNET_4: {"input": 3.00, "output": 15.00},
    AIModel.CLAUDE_SONNET_4_5: {"input": 3.00, "output": 15.00},
    AIModel.CLAUDE_OPUS_4: {"input": 15.00, "output": 75.00},
    AIModel.CLAUDE_OPUS_4_5: {"input": 15.00, "output": 75.00},
    # Google
    AIModel.GEMINI_15_PRO: {"input": 1.25, "output": 5.00},
    AIModel.GEMINI_15_FLASH: {"input": 0.075, "output": 0.30},
    AIModel.GEMINI_20_PRO: {"input": 2.50, "output": 10.00},
    # Mistral
    AIModel.MISTRAL_LARGE: {"input": 4.00, "output": 12.00},
    AIModel.MISTRAL_MEDIUM: {"input": 2.70, "output": 8.10},
    AIModel.MISTRAL_SMALL: {"input": 1.00, "output": 3.00},
}

# Default agent configuration values
DEFAULT_AGENT_CONFIG = {
    "model": AIModel.CLAUDE_SONNET_4_5,
    "max_iterations": 30,
    "max_tool_calls": 50,
    "temperature": 0.7,
    "max_tokens": 4096,
}

# Default execution configuration
DEFAULT_EXECUTION_CONFIG = {
    "timeout_seconds": 300,  # 5 minutes
    "max_retries": 3,
    "retry_delay_seconds": 5,
}

# Tool execution limits
TOOL_EXECUTION_LIMITS = {
    "timeout_seconds": 30,
    "max_output_size_bytes": 1_000_000,  # 1MB
    "max_memory_mb": 256,
}

# API rate limits (per minute)
API_RATE_LIMITS = {
    "events": 1000,
    "functions": 100,
    "runs": 500,
    "tools": 100,
}

# Streaming configuration
STREAMING_CONFIG = {
    "keepalive_interval_seconds": 15,
    "default_timeout_seconds": 300,
    "max_timeout_seconds": 600,
    "buffer_size": 100,  # Max buffered events per run
}

# Approval configuration
APPROVAL_CONFIG = {
    "default_timeout": "1h",
    "max_timeout": "24h",
    "poll_interval_seconds": 1,
}


def get_model_pricing(model: str) -> ModelPricing:
    """
    Get pricing for a model.

    Args:
        model: The model name or AIModel enum value

    Returns:
        ModelPricing dict with input and output costs per 1M tokens
    """
    # Handle both string and enum
    model_str = model.value if isinstance(model, AIModel) else model

    # Direct match
    if model_str in MODEL_PRICING:
        return MODEL_PRICING[model_str]

    # Try to find a partial match (for model versions)
    for known_model, pricing in MODEL_PRICING.items():
        known_str = known_model.value if isinstance(known_model, AIModel) else known_model
        if model_str.startswith(known_str) or known_str.startswith(model_str):
            return pricing

    # Default pricing (estimate)
    return {"input": 5.00, "output": 15.00}


def calculate_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """
    Calculate the cost for a model call.

    Args:
        model: The model name
        prompt_tokens: Number of input tokens
        completion_tokens: Number of output tokens

    Returns:
        Estimated cost in USD
    """
    pricing = get_model_pricing(model)
    input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output"]
    return input_cost + output_cost
