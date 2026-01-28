"""Event ingestion and management endpoints."""

from datetime import datetime
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge_server.db import get_session
from flowforge_server.db.models import Event, Function, Run, RunStatus, Tenant
from flowforge_server.stream import StreamMessage
from flowforge_server.api.schemas.events import (
    EventCreate,
    EventResponse,
    EventsResponse,
)
from flowforge_server.api.deps import TenantWithDevFallback
from flowforge_server.services.container import get_services
from flowforge_server.logging import Loggers

router = APIRouter(prefix="/events", tags=["events"])
log = Loggers.api()


@router.post("", response_model=EventResponse, status_code=201)
async def create_event(
    request: Request,
    event_data: EventCreate,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> EventResponse:
    """
    Ingest a new event.

    Events trigger matching functions based on their name.
    Use the `id` field for idempotency - duplicate IDs will be rejected.

    Events are published to a stream for async processing by the Runner service.
    The response includes the run_id if a matching function was found.
    """
    # Generate event ID if not provided
    event_id = event_data.id or str(uuid.uuid4())
    now = datetime.utcnow()

    # Check for duplicate event ID (idempotency)
    existing = await session.execute(
        select(Event).where(
            Event.tenant_id == tenant.id,
            Event.event_id == event_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"Event with ID '{event_id}' already exists",
        )

    # Create event record
    event = Event(
        tenant_id=tenant.id,
        event_id=event_id,
        name=event_data.name,
        data=event_data.data,
        timestamp=event_data.timestamp or now,
        received_at=now,
        user_id=event_data.user_id,
        processed=False,
    )

    session.add(event)
    await session.flush()

    # Find matching function and create run synchronously
    # This gives the client an immediate run_id for SSE connection
    run_id: str | None = None
    fn_result = await session.execute(
        select(Function).where(
            Function.tenant_id == tenant.id,
            Function.trigger_type == "event",
            Function.trigger_value == event_data.name,
            Function.is_active == True,
        )
    )
    fn = fn_result.scalar_one_or_none()

    if fn:
        # Create run in pending status (gives client immediate run_id for SSE)
        run = Run(
            tenant_id=tenant.id,
            function_id=fn.id,
            event_id=event.id,
            status=RunStatus.PENDING,
            trigger_type="event",
            trigger_data={
                "event": {
                    "id": event_id,
                    "name": event_data.name,
                    "data": event_data.data,
                    "timestamp": event.timestamp.isoformat(),
                }
            },
            attempt=1,
            max_attempts=fn.retries + 1 if hasattr(fn, 'retries') else 3,
        )
        session.add(run)
        await session.flush()
        run_id = str(run.id)
        log.info("run_created", run_id=run_id, function_id=fn.function_id)

    # Publish to event stream for Runner to process and enqueue job
    # This decouples the API from job scheduling for better scalability
    services = get_services(request)
    message = StreamMessage(
        id=str(event.id),
        event_name=event_data.name,
        event_id=event_id,
        event_data=event_data.data,
        tenant_id=str(tenant.id),
        timestamp=event.timestamp,
        # Include run_id so Runner knows not to create duplicate run
        run_id=run_id,
    )

    try:
        await services.event_stream.publish(message)
        event.processed = True
    except Exception as e:
        # Event is stored and can be reprocessed
        log.warning("event_stream_publish_failed", event_id=event_id, error=str(e))

    await session.commit()
    await session.refresh(event)

    return EventResponse(
        id=str(event.id),
        event_id=event.event_id,
        name=event.name,
        data=event.data,
        timestamp=event.timestamp,
        received_at=event.received_at,
        user_id=event.user_id,
        processed=event.processed,
        run_id=run_id,
    )


@router.get("", response_model=EventsResponse)
async def list_events(
    tenant: TenantWithDevFallback,
    name: str | None = Query(None, description="Filter by event name"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_session),
) -> EventsResponse:
    """List events with optional filtering."""
    query = select(Event).where(Event.tenant_id == tenant.id)

    if name:
        query = query.where(Event.name == name)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    # Get paginated results
    query = query.order_by(Event.received_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    events = result.scalars().all()

    return EventsResponse(
        events=[
            EventResponse(
                id=str(e.id),
                event_id=e.event_id,
                name=e.name,
                data=e.data,
                timestamp=e.timestamp,
                received_at=e.received_at,
                user_id=e.user_id,
                processed=e.processed,
            )
            for e in events
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: str,
    tenant: TenantWithDevFallback,
    session: AsyncSession = Depends(get_session),
) -> EventResponse:
    """Get a specific event by ID."""
    result = await session.execute(
        select(Event).where(
            Event.tenant_id == tenant.id,
            Event.event_id == event_id,
        )
    )
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return EventResponse(
        id=str(event.id),
        event_id=event.event_id,
        name=event.name,
        data=event.data,
        timestamp=event.timestamp,
        received_at=event.received_at,
        user_id=event.user_id,
        processed=event.processed,
    )
