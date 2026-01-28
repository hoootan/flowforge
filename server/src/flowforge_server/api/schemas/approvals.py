"""Pydantic schemas for approval-related API operations."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ToolApprovalResponse(BaseModel):
    """Schema for tool approval API response."""

    id: str = Field(..., description="Approval ID")
    run_id: str = Field(..., description="Run ID")
    step_id: str = Field(..., description="Step ID")
    tool_name: str = Field(..., description="Tool name")
    tool_call_id: str = Field(..., description="Tool call ID")
    tool_arguments: dict[str, Any] = Field(..., description="Tool arguments")
    status: str = Field(..., description="Approval status")
    requested_at: datetime = Field(..., description="When approval was requested")
    timeout_at: datetime = Field(..., description="When approval times out")
    resolved_at: datetime | None = Field(None, description="When approval was resolved")
    resolved_by: str | None = Field(None, description="Who resolved the approval")
    rejection_reason: str | None = Field(None, description="Reason for rejection")
    created_at: datetime = Field(..., description="When approval was created")

    model_config = {"from_attributes": True}


class ApprovalsResponse(BaseModel):
    """Schema for listing approvals."""

    approvals: list[ToolApprovalResponse]
    total: int
    page: int = 1
    page_size: int = 50


class ApproveToolRequest(BaseModel):
    """Schema for approving a tool call."""

    resolved_by: str | None = Field(
        None,
        description="Identifier of who approved the tool call",
    )
    modified_arguments: dict[str, Any] | None = Field(
        None,
        description="Modified or additional arguments (e.g., user input for ask_user tool)",
    )


class RejectToolRequest(BaseModel):
    """Schema for rejecting a tool call."""

    reason: str = Field(..., description="Reason for rejection")
    resolved_by: str | None = Field(
        None,
        description="Identifier of who rejected the tool call",
    )


class ApprovalActionResponse(BaseModel):
    """Schema for approval action responses (approve/reject)."""

    success: bool
    message: str
    approval_id: str


class ToolCallResponse(BaseModel):
    """Schema for tool call information."""

    step_id: str = Field(..., description="Step ID")
    tool_name: str | None = Field(None, description="Tool name")
    tool_call_id: str | None = Field(None, description="Tool call ID")
    tool_input: dict[str, Any] | None = Field(None, description="Tool input")
    tool_output: dict[str, Any] | None = Field(None, description="Tool output")
    status: str = Field(..., description="Step status")
    started_at: datetime | None = Field(None, description="When tool call started")
    ended_at: datetime | None = Field(None, description="When tool call ended")

    model_config = {"from_attributes": True}


class ToolCallsResponse(BaseModel):
    """Schema for listing tool calls."""

    tool_calls: list[ToolCallResponse]
    total: int
