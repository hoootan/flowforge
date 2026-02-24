"""Constants and enumerations for FlowForge.

This module centralizes configuration constants, model definitions,
and pricing information used across the application.
"""

from enum import Enum
from typing import TypedDict


class AIModel(str, Enum):
    """Supported AI models."""

    # OpenAI GPT-5 family
    GPT_5_2 = "gpt-5.2"
    GPT_5_1 = "gpt-5.1"
    GPT_5 = "gpt-5"
    GPT_5_MINI = "gpt-5-mini"
    GPT_5_NANO = "gpt-5-nano"
    # OpenAI GPT-4.1 family
    GPT_4_1 = "gpt-4.1"
    GPT_4_1_MINI = "gpt-4.1-mini"
    # OpenAI reasoning models
    O1 = "o1"
    O3 = "o3"
    O3_MINI = "o3-mini"
    O4_MINI = "o4-mini"

    # Anthropic models
    CLAUDE_OPUS_4_6 = "claude-opus-4-6"
    CLAUDE_SONNET_4_6 = "claude-sonnet-4-6"
    CLAUDE_HAIKU_4_5 = "claude-haiku-4-5-20251001"

    # Google models
    GEMINI_25_PRO = "gemini-2.5-pro"
    GEMINI_25_FLASH = "gemini-2.5-flash"

    # Mistral models
    MISTRAL_LARGE = "mistral-large-latest"
    MISTRAL_MEDIUM = "mistral-medium-latest"
    MISTRAL_SMALL = "mistral-small-latest"


class ModelPricing(TypedDict):
    """Pricing structure for a model (per 1M tokens)."""

    input: float
    output: float


# Model pricing (per 1M tokens) - updated February 2026
MODEL_PRICING: dict[str, ModelPricing] = {
    # OpenAI
    AIModel.GPT_5_2: {"input": 1.75, "output": 14.00},
    AIModel.GPT_5_1: {"input": 1.25, "output": 10.00},
    AIModel.GPT_5: {"input": 1.25, "output": 10.00},
    AIModel.GPT_5_MINI: {"input": 0.25, "output": 2.00},
    AIModel.GPT_5_NANO: {"input": 0.05, "output": 0.40},
    AIModel.GPT_4_1: {"input": 2.00, "output": 8.00},
    AIModel.GPT_4_1_MINI: {"input": 0.40, "output": 1.60},
    AIModel.O1: {"input": 15.00, "output": 60.00},
    AIModel.O3: {"input": 2.00, "output": 8.00},
    AIModel.O3_MINI: {"input": 1.10, "output": 4.40},
    AIModel.O4_MINI: {"input": 1.10, "output": 4.40},
    # Anthropic
    AIModel.CLAUDE_OPUS_4_6: {"input": 5.00, "output": 25.00},
    AIModel.CLAUDE_SONNET_4_6: {"input": 3.00, "output": 15.00},
    AIModel.CLAUDE_HAIKU_4_5: {"input": 1.00, "output": 5.00},
    # Google
    AIModel.GEMINI_25_PRO: {"input": 1.25, "output": 10.00},
    AIModel.GEMINI_25_FLASH: {"input": 0.30, "output": 2.50},
    # Mistral
    AIModel.MISTRAL_LARGE: {"input": 4.00, "output": 12.00},
    AIModel.MISTRAL_MEDIUM: {"input": 2.70, "output": 8.10},
    AIModel.MISTRAL_SMALL: {"input": 1.00, "output": 3.00},
}

# Default agent configuration values
DEFAULT_AGENT_CONFIG = {
    "model": AIModel.CLAUDE_SONNET_4_6,
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
