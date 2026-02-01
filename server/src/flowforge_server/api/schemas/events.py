"""Pydantic schemas for event-related API operations."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EventCreate(BaseModel):
    """Schema for creating a new event."""

    id: str | None = Field(
        None,
        description="Optional client-provided event ID for idempotency",
        examples=["evt_123abc"],
    )

    name: str = Field(
        ...,
        description="Event type name",
        examples=["order/created", "user/signup"],
        min_length=1,
        max_length=255,
    )

    data: dict[str, Any] = Field(
        default_factory=dict,
        description="Event payload data",
        examples=[{"order_id": "123", "total": 99.99}],
    )

    timestamp: datetime | None = Field(
        None,
        description="When the event occurred (defaults to now)",
    )

    user_id: str | None = Field(
        None,
        description="Optional user ID associated with the event",
        examples=["user_456"],
    )


class EventResponse(BaseModel):
    """Schema for event API response."""

    id: str = Field(..., description="Internal event ID")
    event_id: str = Field(..., description="Client-provided or generated event ID")
    name: str = Field(..., description="Event type name")
    data: dict[str, Any] = Field(..., description="Event payload")
    timestamp: datetime = Field(..., description="Event timestamp")
    received_at: datetime = Field(..., description="When server received the event")
    user_id: str | None = Field(None, description="Associated user ID")
    processed: bool = Field(..., description="Whether the event has been processed")
    run_id: str | None = Field(None, description="ID of the run triggered by this event")

    model_config = {"from_attributes": True}


class EventsResponse(BaseModel):
    """Schema for listing events."""

    events: list[EventResponse]
    total: int
    page: int = 1
    page_size: int = 50


class BatchEventCreate(BaseModel):
    """Schema for creating multiple events in a batch."""

    events: list[EventCreate] = Field(
        ...,
        description="List of events to create",
        min_length=1,
        max_length=100,
    )


class BatchEventResult(BaseModel):
    """Result for a single event in a batch."""

    index: int = Field(..., description="Index of the event in the batch")
    success: bool = Field(..., description="Whether the event was created successfully")
    id: str | None = Field(None, description="Internal event ID if successful")
    event_id: str | None = Field(None, description="Event ID if successful")
    run_id: str | None = Field(None, description="Run ID if a function was triggered")
    error: str | None = Field(None, description="Error message if failed")


class BatchEventResponse(BaseModel):
    """Response for batch event creation."""

    total: int = Field(..., description="Total events in batch")
    success_count: int = Field(..., description="Number of successfully created events")
    failure_count: int = Field(..., description="Number of failed events")
    results: list[BatchEventResult] = Field(..., description="Results for each event")
