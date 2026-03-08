"""Pydantic schemas for function-related API operations."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TriggerSchema(BaseModel):
    """Schema for function trigger configuration."""

    type: str = Field(
        ...,
        description="Trigger type: 'event', 'cron', or 'webhook'",
        examples=["event"],
    )

    value: str = Field(
        ...,
        description="Trigger value (event name, cron expression, or webhook path)",
        examples=["order/created", "0 9 * * *"],
    )

    expression: str | None = Field(
        None,
        description="Optional filter expression for event triggers",
        examples=["event.data.amount > 100"],
    )


class SubAgentConfigSchema(BaseModel):
    """Schema for a sub-agent configuration within an inline function."""

    system_prompt: str = Field(
        ...,
        description="System prompt for the sub-agent",
    )

    model: str | None = Field(
        default=None,
        description="Model override for the sub-agent (defaults to parent model)",
    )

    tools: list[str] = Field(
        default_factory=list,
        description="Tool names available to the sub-agent",
    )

    max_iterations: int = Field(
        default=15,
        description="Maximum agent loop iterations for the sub-agent",
        ge=1,
        le=50,
    )

    max_tool_calls: int = Field(
        default=30,
        description="Maximum tool calls for the sub-agent",
        ge=1,
        le=100,
    )

    description: str | None = Field(
        default=None,
        description="Description shown to the parent agent LLM",
    )


class AgentConfigSchema(BaseModel):
    """Schema for agent configuration in inline functions."""

    model: str = Field(
        default="claude-sonnet-4-6",
        description="AI model to use",
        examples=["claude-sonnet-4-6", "gpt-5.3"],
    )

    max_iterations: int = Field(
        default=30,
        description="Maximum agent loop iterations",
        ge=1,
        le=100,
    )

    max_tool_calls: int = Field(
        default=50,
        description="Maximum tool calls per run",
        ge=1,
        le=200,
    )

    sub_agents: dict[str, SubAgentConfigSchema] = Field(
        default_factory=dict,
        description="Sub-agent definitions keyed by name",
    )


class FunctionCreate(BaseModel):
    """Schema for registering a new function (worker mode)."""

    id: str = Field(
        ...,
        description="Unique function identifier",
        examples=["process-order"],
        min_length=1,
        max_length=255,
    )

    name: str = Field(
        ...,
        description="Human-readable function name",
        examples=["Process Order"],
    )

    trigger: TriggerSchema = Field(
        ...,
        description="How the function is triggered",
    )

    endpoint_url: str = Field(
        ...,
        description="URL where the function is deployed",
        examples=["https://myapp.com/api/flowforge"],
    )

    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Function configuration (retries, timeout, etc.)",
        examples=[{"retries": 3, "timeout": "5m"}],
    )


class InlineFunctionCreate(BaseModel):
    """Schema for creating an inline/serverless function."""

    id: str = Field(
        ...,
        description="Unique function identifier",
        examples=["create-social-post"],
        min_length=1,
        max_length=255,
    )

    name: str = Field(
        ...,
        description="Human-readable function name",
        examples=["Create Social Post"],
    )

    trigger: TriggerSchema = Field(
        ...,
        description="How the function is triggered",
    )

    system_prompt: str = Field(
        ...,
        description="System prompt for the agent",
        examples=["You are a social media content creator..."],
    )

    tools: list[str] = Field(
        default_factory=list,
        description="List of tool names to use (must exist in tools table). Can be empty for text-only agents.",
        examples=[["web_search", "generate_image", "ask_user"]],
    )

    agent_config: AgentConfigSchema = Field(
        default_factory=AgentConfigSchema,
        description="Agent configuration (model, iterations, etc.)",
    )

    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Function configuration (retries, timeout, etc.)",
        examples=[{"retries": 3, "timeout": "30m"}],
    )


class FunctionUpdate(BaseModel):
    """Schema for updating a function."""

    name: str | None = Field(None, description="Updated function name")
    endpoint_url: str | None = Field(None, description="Updated endpoint URL")
    system_prompt: str | None = Field(None, description="Updated system prompt (inline only)")
    tools: list[str] | None = Field(None, description="Updated tool list (inline only)")
    agent_config: AgentConfigSchema | None = Field(None, description="Updated agent config (inline only)")
    config: dict[str, Any] | None = Field(None, description="Updated configuration")
    is_active: bool | None = Field(None, description="Whether the function is active")


class FunctionResponse(BaseModel):
    """Schema for function API response."""

    id: str = Field(..., description="Internal function ID")
    function_id: str = Field(..., description="User-defined function ID")
    name: str = Field(..., description="Function name")
    trigger_type: str = Field(..., description="Trigger type")
    trigger_value: str = Field(..., description="Trigger value")
    trigger_expression: str | None = Field(None, description="Filter expression")
    endpoint_url: str | None = Field(None, description="Deployment URL (None for inline)")
    is_inline: bool = Field(default=False, description="Whether this is an inline/serverless function")
    system_prompt: str | None = Field(None, description="System prompt (inline only)")
    tools_config: list[str] | None = Field(None, description="Tool names (inline only)")
    agent_config: dict[str, Any] | None = Field(None, description="Agent config (inline only)")
    config: dict[str, Any] = Field(..., description="Function configuration")
    is_active: bool = Field(..., description="Whether the function is active")
    created_at: datetime = Field(..., description="When the function was created")
    updated_at: datetime = Field(..., description="When the function was last updated")

    model_config = {"from_attributes": True}


class FunctionsResponse(BaseModel):
    """Schema for listing functions."""

    functions: list[FunctionResponse]
    total: int
