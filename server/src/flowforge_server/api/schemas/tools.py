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

    code: str | None = Field(
        None,
        description="Python code for the tool. Format: async def execute(**kwargs) -> dict: ...",
        examples=["async def execute(query: str) -> dict:\n    return {'answer': f'Results for {query}'}"],
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
    code: str | None = Field(None, description="Updated Python code")
    requires_approval: bool | None = Field(None, description="Updated approval requirement")
    approval_timeout: str | None = Field(None, description="Updated approval timeout")
    is_active: bool | None = Field(None, description="Whether the tool is active")


class ToolResponse(BaseModel):
    """Schema for tool API response."""

    id: str = Field(..., description="Tool ID")
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    parameters: dict[str, Any] = Field(..., description="Parameter schema")
    code: str | None = Field(None, description="Python code (None for built-in)")
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
