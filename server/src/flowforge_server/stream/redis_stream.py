"""Redis Streams implementation for event streaming."""

import json
from datetime import datetime
from typing import Any

import redis.asyncio as redis

from flowforge_server.stream.base import EventStream, StreamMessage
from flowforge_server.config import get_settings


class RedisEventStream(EventStream):
    """
    Redis Streams-based event stream implementation.

    Uses Redis Streams for reliable, ordered event delivery
    with consumer groups for load balancing.
    """

    def __init__(
        self,
        redis_url: str | None = None,
        stream_name: str = "flowforge:events",
        max_len: int = 100000,
    ) -> None:
        """
        Initialize Redis event stream.

        Args:
            redis_url: Redis connection URL.
            stream_name: Name of the Redis stream.
            max_len: Maximum stream length (older entries trimmed).
        """
        settings = get_settings()
        self.redis_url = redis_url or settings.redis_url
        self.stream_name = stream_name
        self.max_len = max_len

        self._client: redis.Redis | None = None
        self._consumer_groups_created: set[str] = set()

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
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _ensure_consumer_group(self, group_name: str) -> None:
        """Ensure consumer group exists."""
        if group_name in self._consumer_groups_created:
            return

        client = await self._get_client()

        try:
            await client.xgroup_create(
                self.stream_name,
                group_name,
                id="0",
                mkstream=True,
            )
        except redis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

        self._consumer_groups_created.add(group_name)

    async def publish(self, message: StreamMessage) -> str:
        """Publish a message to the stream."""
        client = await self._get_client()

        # Serialize message
        data = {
            "data": json.dumps(message.to_dict()),
        }

        # Add to stream with approximate max length
        stream_id = await client.xadd(
            self.stream_name,
            data,
            maxlen=self.max_len,
            approximate=True,
        )

        message.stream_id = stream_id
        return stream_id

    async def subscribe(
        self,
        consumer_group: str,
        consumer_name: str,
        count: int = 10,
        block_ms: int = 5000,
    ) -> list[StreamMessage]:
        """Subscribe to the stream and get messages."""
        client = await self._get_client()

        # Ensure consumer group exists
        await self._ensure_consumer_group(consumer_group)

        # Read new messages for this consumer
        try:
            results = await client.xreadgroup(
                groupname=consumer_group,
                consumername=consumer_name,
                streams={self.stream_name: ">"},
                count=count,
                block=block_ms,
            )
        except redis.ResponseError as e:
            if "NOGROUP" in str(e):
                await self._ensure_consumer_group(consumer_group)
                return []
            raise

        if not results:
            return []

        messages = []
        for stream_name, stream_messages in results:
            for stream_id, data in stream_messages:
                try:
                    message_data = json.loads(data.get("data", "{}"))
                    message = StreamMessage.from_dict(message_data)
                    message.stream_id = stream_id
                    messages.append(message)
                except json.JSONDecodeError:
                    # Skip malformed messages
                    continue

        return messages

    async def acknowledge(self, message_ids: list[str]) -> int:
        """Acknowledge messages as processed."""
        if not message_ids:
            return 0

        client = await self._get_client()

        # We need to know the consumer group to ack
        # In practice, each consumer group needs its own ack
        # For now, we'll use a default group
        count = 0
        for group in self._consumer_groups_created:
            try:
                result = await client.xack(self.stream_name, group, *message_ids)
                count += result
            except redis.ResponseError:
                pass

        return count

    async def acknowledge_for_group(
        self,
        consumer_group: str,
        message_ids: list[str],
    ) -> int:
        """Acknowledge messages for a specific consumer group."""
        if not message_ids:
            return 0

        client = await self._get_client()

        try:
            return await client.xack(self.stream_name, consumer_group, *message_ids)
        except redis.ResponseError:
            return 0

    async def get_pending(
        self,
        consumer_group: str,
        count: int = 10,
    ) -> list[StreamMessage]:
        """Get pending messages that haven't been acknowledged."""
        client = await self._get_client()

        # Ensure consumer group exists
        await self._ensure_consumer_group(consumer_group)

        try:
            # Get pending entries summary
            pending_info = await client.xpending(
                self.stream_name,
                consumer_group,
            )

            if not pending_info or pending_info["pending"] == 0:
                return []

            # Get detailed pending entries
            pending_entries = await client.xpending_range(
                self.stream_name,
                consumer_group,
                min="-",
                max="+",
                count=count,
            )

            if not pending_entries:
                return []

            # Claim and return the messages
            message_ids = [entry["message_id"] for entry in pending_entries]

            # Claim messages that have been pending for > 30 seconds
            claimed = await client.xclaim(
                self.stream_name,
                consumer_group,
                "recovery-consumer",
                min_idle_time=30000,  # 30 seconds
                message_ids=message_ids,
            )

            messages = []
            for stream_id, data in claimed:
                try:
                    message_data = json.loads(data.get("data", "{}"))
                    message = StreamMessage.from_dict(message_data)
                    message.stream_id = stream_id
                    message.attempts += 1
                    messages.append(message)
                except json.JSONDecodeError:
                    continue

            return messages

        except redis.ResponseError:
            return []

    async def get_stream_info(self) -> dict[str, Any]:
        """Get information about the stream."""
        client = await self._get_client()

        try:
            info = await client.xinfo_stream(self.stream_name)
            return {
                "length": info.get("length", 0),
                "first_entry": info.get("first-entry"),
                "last_entry": info.get("last-entry"),
                "groups": info.get("groups", 0),
            }
        except redis.ResponseError:
            return {"length": 0, "groups": 0}

    async def get_consumer_groups(self) -> list[dict[str, Any]]:
        """Get information about consumer groups."""
        client = await self._get_client()

        try:
            groups = await client.xinfo_groups(self.stream_name)
            return [
                {
                    "name": g.get("name"),
                    "consumers": g.get("consumers", 0),
                    "pending": g.get("pending", 0),
                    "last_delivered_id": g.get("last-delivered-id"),
                }
                for g in groups
            ]
        except redis.ResponseError:
            return []

    async def trim(self, max_len: int | None = None) -> int:
        """Trim the stream to a maximum length."""
        client = await self._get_client()
        target_len = max_len or self.max_len

        try:
            return await client.xtrim(self.stream_name, maxlen=target_len)
        except redis.ResponseError:
            return 0
