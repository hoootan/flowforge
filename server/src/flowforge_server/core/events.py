"""Event processing service."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge_server.db.models import Event, Function
from flowforge_server.stream import RedisEventStream, StreamMessage


class EventService:
    """
    Service for event processing.

    Handles:
    - Event ingestion and storage
    - Publishing to event stream
    - Event validation
    """

    def __init__(self) -> None:
        self.event_stream = RedisEventStream()

    async def ingest(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        event_name: str,
        event_data: dict[str, Any],
        event_id: str | None = None,
        timestamp: datetime | None = None,
        user_id: str | None = None,
    ) -> Event:
        """
        Ingest an event and publish to the stream.

        Args:
            session: Database session.
            tenant_id: Tenant UUID.
            event_name: Event type name.
            event_data: Event payload.
            event_id: Optional client-provided ID for idempotency.
            timestamp: Optional event timestamp.
            user_id: Optional user ID.

        Returns:
            The created Event record.
        """
        event_id = event_id or str(uuid.uuid4())
        now = datetime.utcnow()

        # Check for duplicate (idempotency)
        existing = await session.execute(
            select(Event).where(
                Event.tenant_id == tenant_id,
                Event.event_id == event_id,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Event with ID '{event_id}' already exists")

        # Create event record
        event = Event(
            tenant_id=tenant_id,
            event_id=event_id,
            name=event_name,
            data=event_data,
            timestamp=timestamp or now,
            received_at=now,
            user_id=user_id,
            processed=False,
        )

        session.add(event)
        await session.flush()

        # Publish to event stream for async processing
        message = StreamMessage(
            id=str(event.id),
            event_name=event_name,
            event_id=event_id,
            event_data=event_data,
            tenant_id=str(tenant_id),
            timestamp=event.timestamp,
        )

        await self.event_stream.publish(message)

        # Mark as processed (published to stream)
        event.processed = True

        return event

    async def get_matching_functions(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        event_name: str,
    ) -> list[Function]:
        """Get functions that match an event."""
        result = await session.execute(
            select(Function).where(
                Function.tenant_id == tenant_id,
                Function.trigger_type == "event",
                Function.trigger_value == event_name,
                Function.is_active == True,
            )
        )
        return list(result.scalars().all())

    async def close(self) -> None:
        """Close resources."""
        await self.event_stream.close()
