"""Redis Pub/Sub for real-time client notifications.

This module provides a pub/sub layer for broadcasting run events
to connected SSE clients in real-time.
"""

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import redis.asyncio as redis

from flowforge_server.config import get_settings


class JSONEncoder(json.JSONEncoder):
    """JSON encoder that handles UUID and datetime objects."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class RunEventType(str, Enum):
    """Types of events that can be broadcast for a run."""

    # Step lifecycle events
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"

    # AI/thinking events
    THINKING = "thinking"
    THINKING_CHUNK = "thinking_chunk"  # For streaming tokens

    # Tool events
    TOOL_CALL_STARTED = "tool_call_started"
    TOOL_CALL_COMPLETED = "tool_call_completed"

    # HITL events
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_RESOLVED = "approval_resolved"

    # Sub-agent events
    SUB_AGENT_STARTED = "sub_agent_started"
    SUB_AGENT_COMPLETED = "sub_agent_completed"

    # Run lifecycle events
    RUN_STARTED = "run_started"
    RUN_PAUSED = "run_paused"
    RUN_RESUMED = "run_resumed"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"


@dataclass
class RunEvent:
    """Event broadcast for a run."""

    run_id: str
    event_type: RunEventType
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "run_id": self.run_id,
            "event_type": self.event_type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RunEvent":
        """Create from dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.utcnow()

        return cls(
            run_id=data["run_id"],
            event_type=RunEventType(data["event_type"]),
            data=data.get("data", {}),
            timestamp=timestamp,
        )

    def to_sse(self) -> str:
        """Convert to SSE format string."""
        return f"event: {self.event_type.value}\ndata: {json.dumps(self.to_dict(), cls=JSONEncoder)}\n\n"


class RunEventPubSub:
    """
    Redis Pub/Sub wrapper for broadcasting run events to SSE clients.

    Uses Redis Pub/Sub channels per run_id for efficient routing.
    Each run gets its own channel: flowforge:run:{run_id}:events
    """

    def __init__(self, redis_url: str | None = None) -> None:
        """Initialize the pub/sub wrapper."""
        settings = get_settings()
        self.redis_url = redis_url or settings.redis_url
        self._client: redis.Redis | None = None
        self._pubsub: redis.client.PubSub | None = None

    def _channel_name(self, run_id: str) -> str:
        """Get the channel name for a run."""
        return f"flowforge:run:{run_id}:events"

    async def _get_client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self._client is None:
            self._client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._client

    async def close(self) -> None:
        """Close Redis connection."""
        if self._pubsub:
            await self._pubsub.close()
            self._pubsub = None

        if self._client:
            await self._client.aclose()
            self._client = None

    def _buffer_key(self, run_id: str) -> str:
        """Get the buffer key for a run."""
        return f"flowforge:run:{run_id}:buffer"

    async def buffer_event(self, event: RunEvent, buffer_ttl: int = 300) -> None:
        """
        Buffer an event for replay when clients connect late.

        Args:
            event: The run event to buffer.
            buffer_ttl: TTL for buffered events in seconds (default 5 minutes).
        """
        client = await self._get_client()
        buffer_key = self._buffer_key(event.run_id)
        message = json.dumps(event.to_dict(), cls=JSONEncoder)

        # Push to list and set TTL
        pipe = client.pipeline()
        pipe.rpush(buffer_key, message)
        pipe.expire(buffer_key, buffer_ttl)
        await pipe.execute()

    async def get_buffered_events(self, run_id: str, clear: bool = False) -> list[RunEvent]:
        """
        Get buffered events for a run.

        Args:
            run_id: The run ID.
            clear: Whether to clear the buffer after reading.

        Returns:
            List of buffered events.
        """
        client = await self._get_client()
        buffer_key = self._buffer_key(run_id)

        # Get all buffered messages
        messages = await client.lrange(buffer_key, 0, -1)

        if clear:
            await client.delete(buffer_key)

        events = []
        for msg in messages:
            try:
                data = json.loads(msg)
                events.append(RunEvent.from_dict(data))
            except (json.JSONDecodeError, KeyError, ValueError):
                continue

        return events

    async def publish(self, event: RunEvent) -> int:
        """
        Publish an event to subscribers of a run.

        Args:
            event: The run event to publish.

        Returns:
            Number of subscribers that received the message.
        """
        client = await self._get_client()
        channel = self._channel_name(event.run_id)
        message = json.dumps(event.to_dict(), cls=JSONEncoder)

        return await client.publish(channel, message)

    async def subscribe(self, run_id: str) -> AsyncIterator[RunEvent]:
        """
        Subscribe to events for a specific run.

        Yields RunEvent objects as they are published.

        Args:
            run_id: The run ID to subscribe to.

        Yields:
            RunEvent objects.
        """
        client = await self._get_client()
        pubsub = client.pubsub()

        channel = self._channel_name(run_id)
        await pubsub.subscribe(channel)

        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        yield RunEvent.from_dict(data)
                    except (json.JSONDecodeError, KeyError, ValueError):
                        # Skip malformed messages
                        continue
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    async def subscribe_with_timeout(
        self,
        run_id: str,
        timeout_seconds: float = 300.0,
    ) -> AsyncIterator[RunEvent]:
        """
        Subscribe to events with a timeout.

        Args:
            run_id: The run ID to subscribe to.
            timeout_seconds: Maximum time to wait for events.

        Yields:
            RunEvent objects.
        """
        client = await self._get_client()
        pubsub = client.pubsub()

        channel = self._channel_name(run_id)
        await pubsub.subscribe(channel)

        try:
            deadline = asyncio.get_event_loop().time() + timeout_seconds

            while True:
                remaining = deadline - asyncio.get_event_loop().time()
                if remaining <= 0:
                    break

                try:
                    message = await asyncio.wait_for(
                        pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0),
                        timeout=min(remaining, 1.0),
                    )

                    if message and message["type"] == "message":
                        try:
                            data = json.loads(message["data"])
                            event = RunEvent.from_dict(data)
                            yield event

                            # Stop if run completed or failed
                            if event.event_type in (
                                RunEventType.RUN_COMPLETED,
                                RunEventType.RUN_FAILED,
                            ):
                                break
                        except (json.JSONDecodeError, KeyError, ValueError):
                            continue

                except TimeoutError:
                    # Timeout is expected, continue polling
                    continue

        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()


# Global instance
_pubsub: RunEventPubSub | None = None


def get_pubsub() -> RunEventPubSub:
    """Get the global pub/sub instance."""
    global _pubsub
    if _pubsub is None:
        _pubsub = RunEventPubSub()
    return _pubsub


async def publish_run_event(
    run_id: str,
    event_type: RunEventType,
    data: dict[str, Any] | None = None,
) -> int:
    """
    Convenience function to publish a run event.

    Also buffers the event in Redis for replay when SSE clients connect.

    Args:
        run_id: The run ID.
        event_type: Type of event.
        data: Optional event data.

    Returns:
        Number of subscribers that received the message.
    """
    pubsub = get_pubsub()
    event = RunEvent(
        run_id=run_id,
        event_type=event_type,
        data=data or {},
    )

    # Also buffer for replay (for clients that connect late)
    await pubsub.buffer_event(event)

    return await pubsub.publish(event)
