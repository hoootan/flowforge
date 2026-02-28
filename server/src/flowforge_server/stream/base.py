"""Base event stream interface."""

import uuid
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class StreamMessage:
    """
    Represents a message in the event stream.

    Messages are events that flow through the system and
    trigger function executions.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Stream position (set by the stream implementation)
    stream_id: str | None = None

    # Event data
    event_name: str = ""
    event_id: str = ""
    event_data: dict[str, Any] = field(default_factory=dict)

    # Tenant for multi-tenancy
    tenant_id: str = ""

    # Run ID (if run was pre-created by API)
    run_id: str | None = None

    # Timestamp
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Processing metadata
    processed: bool = False
    attempts: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "stream_id": self.stream_id,
            "event_name": self.event_name,
            "event_id": self.event_id,
            "event_data": self.event_data,
            "tenant_id": self.tenant_id,
            "run_id": self.run_id,
            "timestamp": self.timestamp.isoformat(),
            "processed": self.processed,
            "attempts": self.attempts,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StreamMessage":
        """Create from dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.utcnow()

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            stream_id=data.get("stream_id"),
            event_name=data.get("event_name", ""),
            event_id=data.get("event_id", ""),
            event_data=data.get("event_data", {}),
            tenant_id=data.get("tenant_id", ""),
            run_id=data.get("run_id"),
            timestamp=timestamp,
            processed=data.get("processed", False),
            attempts=data.get("attempts", 0),
        )


class EventStream(ABC):
    """
    Abstract base class for event stream implementations.

    Event streams provide at-least-once delivery of events
    to consumers (Runners).
    """

    @abstractmethod
    async def publish(self, message: StreamMessage) -> str:
        """
        Publish a message to the stream.

        Args:
            message: The message to publish.

        Returns:
            The stream message ID.
        """
        pass

    @abstractmethod
    async def subscribe(
        self,
        consumer_group: str,
        consumer_name: str,
        count: int = 10,
        block_ms: int = 5000,
    ) -> list[StreamMessage]:
        """
        Subscribe to the stream and get messages.

        Args:
            consumer_group: Consumer group name for load balancing.
            consumer_name: Unique name for this consumer.
            count: Maximum messages to retrieve.
            block_ms: How long to block waiting for messages.

        Returns:
            List of messages.
        """
        pass

    @abstractmethod
    async def acknowledge(self, message_ids: list[str]) -> int:
        """
        Acknowledge messages as processed.

        Args:
            message_ids: Stream message IDs to acknowledge.

        Returns:
            Number of messages acknowledged.
        """
        pass

    @abstractmethod
    async def get_pending(
        self,
        consumer_group: str,
        count: int = 10,
    ) -> list[StreamMessage]:
        """
        Get pending messages that haven't been acknowledged.

        Used for reprocessing failed messages.

        Args:
            consumer_group: Consumer group name.
            count: Maximum messages to retrieve.

        Returns:
            List of pending messages.
        """
        pass

    async def consume(
        self,
        consumer_group: str,
        consumer_name: str,
        batch_size: int = 10,
    ) -> AsyncIterator[StreamMessage]:
        """
        Continuously consume messages from the stream.

        Yields:
            StreamMessage objects as they become available.
        """
        while True:
            messages = await self.subscribe(
                consumer_group=consumer_group,
                consumer_name=consumer_name,
                count=batch_size,
            )

            for message in messages:
                yield message
