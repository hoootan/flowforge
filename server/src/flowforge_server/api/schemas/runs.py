"""Pydantic schemas for run-related API operations."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class StepResponse(BaseModel):
    """Schema for step API response."""

    id: str = Field(..., description="Step ID")
    step_id: str = Field(..., description="User-defined step ID")
    step_type: str = Field(..., description="Type of step")
    status: str = Field(..., description="Current status")
    input: dict[str, Any] | None = Field(None, description="Step input")
    output: dict[str, Any] | None = Field(None, description="Step output")
    error: dict[str, Any] | None = Field(None, description="Error details")
    attempt: int = Field(..., description="Current attempt number")
    max_attempts: int = Field(..., description="Maximum attempts")
    tool_name: str | None = Field(None, description="Tool name (for agent steps)")
    tool_call_id: str | None = Field(None, description="Tool call ID (for agent steps)")
    tool_input: dict[str, Any] | None = Field(None, description="Tool input arguments")
    tool_output: dict[str, Any] | None = Field(None, description="Tool output result")
    agent_state: dict[str, Any] | None = Field(None, description="Agent state snapshot")
    started_at: datetime | None = Field(None, description="When step started")
    ended_at: datetime | None = Field(None, description="When step ended")
    created_at: datetime = Field(..., description="When step was created")

    model_config = {"from_attributes": True}


class RunResponse(BaseModel):
    """Schema for run API response."""

    id: str = Field(..., description="Run ID")
    function_id: str = Field(..., description="Function ID")
    event_id: str | None = Field(None, description="Triggering event ID")
    status: str = Field(..., description="Current status")
    trigger_type: str = Field(..., description="How the run was triggered")
    trigger_data: dict[str, Any] = Field(..., description="Trigger data")
    attempt: int = Field(..., description="Current attempt number")
    max_attempts: int = Field(..., description="Maximum attempts")
    output: dict[str, Any] | None = Field(None, description="Function output")
    error: dict[str, Any] | None = Field(None, description="Error details")
    started_at: datetime | None = Field(None, description="When run started")
    ended_at: datetime | None = Field(None, description="When run ended")
    created_at: datetime = Field(..., description="When run was created")
    steps: list[StepResponse] = Field(default_factory=list, description="Run steps")

    model_config = {"from_attributes": True}


class RunsResponse(BaseModel):
    """Schema for listing runs."""

    runs: list[RunResponse]
    total: int
    page: int = 1
    page_size: int = 50


class RunActionResponse(BaseModel):
    """Schema for run action responses (cancel, replay)."""

    success: bool
    message: str
    run_id: str
