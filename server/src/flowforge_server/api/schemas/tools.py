"""Pydantic schemas for tool-related API operations."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ToolCreate(BaseModel):
    """Schema for creating a new tool."""

    name: str = Field(
        ...,
        description="Unique tool name",
        examples=["web_search"],
        min_length=1,
        max_length=255,
    )

    description: str = Field(
        ...,
        description="Description of what the tool does (shown to LLM)",
        examples=["Search the web for current information"],
    )

    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON Schema for tool parameters",
        examples=[{
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"]
        }],
    )

    tool_type: str = Field(
        default="custom",
        description="Tool type: 'custom' (code), 'webhook' (HTTP config), or 'builtin'",
        examples=["custom", "webhook"],
    )

    code: str | None = Field(
        None,
        description="Python code for the tool. Format: async def execute(**kwargs) -> dict: ...",
        examples=["async def execute(query: str) -> dict:\n    return {'answer': f'Results for {query}'}"],
    )

    webhook_url: str | None = Field(
        None,
        description="Webhook URL for tool_type='webhook'. Supports {{credential:name}} placeholders.",
        examples=["https://api.example.com/v1/data"],
    )

    webhook_method: str = Field(
        default="POST",
        description="HTTP method for webhook tools",
        examples=["GET", "POST"],
    )

    webhook_headers: dict[str, str] | None = Field(
        None,
        description="HTTP headers for webhook tools. Supports {{credential:name}} placeholders.",
        examples=[{"Authorization": "Bearer {{credential:my_token}}"}],
    )

    requires_approval: bool = Field(
        default=False,
        description="Whether this tool requires human approval before execution",
    )

    approval_timeout: str | None = Field(
        None,
        description="Timeout for approval (e.g., '1h', '30m')",
        examples=["1h"],
    )


class ToolUpdate(BaseModel):
    """Schema for updating a tool."""

    description: str | None = Field(None, description="Updated description")
    parameters: dict[str, Any] | None = Field(None, description="Updated parameters schema")
    tool_type: str | None = Field(None, description="Updated tool type")
    code: str | None = Field(None, description="Updated Python code")
    webhook_url: str | None = Field(None, description="Updated webhook URL")
    webhook_method: str | None = Field(None, description="Updated webhook method")
    webhook_headers: dict[str, str] | None = Field(None, description="Updated webhook headers")
    requires_approval: bool | None = Field(None, description="Updated approval requirement")
    approval_timeout: str | None = Field(None, description="Updated approval timeout")
    is_active: bool | None = Field(None, description="Whether the tool is active")


class ToolResponse(BaseModel):
    """Schema for tool API response."""

    id: str = Field(..., description="Tool ID")
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    parameters: dict[str, Any] = Field(..., description="Parameter schema")
    tool_type: str = Field(default="custom", description="Tool type")
    code: str | None = Field(None, description="Python code (None for built-in)")
    webhook_url: str | None = Field(None, description="Webhook URL")
    webhook_method: str = Field(default="POST", description="Webhook HTTP method")
    webhook_headers: dict[str, str] | None = Field(None, description="Webhook headers")
    is_builtin: bool = Field(..., description="Whether this is a built-in tool")
    requires_approval: bool = Field(..., description="Whether approval is required")
    approval_timeout: str | None = Field(None, description="Approval timeout")
    is_active: bool = Field(..., description="Whether the tool is active")
    created_at: datetime = Field(..., description="When the tool was created")
    updated_at: datetime = Field(..., description="When the tool was last updated")

    model_config = {"from_attributes": True}


class ToolsResponse(BaseModel):
    """Schema for listing tools."""

    tools: list[ToolResponse]
    total: int
