"""Dead Letter Queue for failed jobs.

Jobs that exceed max retry attempts are moved to the DLQ for manual inspection
and possible re-processing.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import redis.asyncio as redis

from flowforge_server.config import get_settings
from flowforge_server.logging import Loggers


@dataclass
class DLQEntry:
    """A job in the Dead Letter Queue."""

    job_id: str
    tenant_id: str
    function_id: str
    original_data: dict[str, Any]
    error: str
    attempts: int
    failed_at: datetime
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "tenant_id": self.tenant_id,
            "function_id": self.function_id,
            "original_data": self.original_data,
            "error": self.error,
            "attempts": self.attempts,
            "failed_at": self.failed_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DLQEntry":
        return cls(
            job_id=data["job_id"],
            tenant_id=data["tenant_id"],
            function_id=data["function_id"],
            original_data=data["original_data"],
            error=data["error"],
            attempts=data["attempts"],
            failed_at=datetime.fromisoformat(data["failed_at"]),
            metadata=data.get("metadata"),
        )


class DeadLetterQueue:
    """
    Redis-based Dead Letter Queue.

    Stores jobs that have failed after all retry attempts for manual inspection.
    Supports requeuing jobs back to the main queue.
    """

    def __init__(
        self,
        redis_url: str | None = None,
        prefix: str = "flowforge",
    ) -> None:
        settings = get_settings()
        self.redis_url = redis_url or settings.redis_url
        self.prefix = prefix
        self._client: redis.Redis | None = None
        self._log = Loggers.api()

        # Key names
        self.dlq_key = f"{prefix}:dlq"
        self.dlq_entries_key = f"{prefix}:dlq:entries"

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

    def _entry_key(self, job_id: str) -> str:
        """Get the key for a DLQ entry."""
        return f"{self.dlq_entries_key}:{job_id}"

    async def add(
        self,
        job_id: str,
        tenant_id: str,
        function_id: str,
        original_data: dict[str, Any],
        error: str,
        attempts: int,
        metadata: dict[str, Any] | None = None,
    ) -> DLQEntry:
        """
        Add a failed job to the Dead Letter Queue.

        Args:
            job_id: Unique job identifier
            tenant_id: Tenant that owns the job
            function_id: Function that failed
            original_data: Original job data for replay
            error: Error message from final failure
            attempts: Number of attempts made
            metadata: Additional context

        Returns:
            The created DLQ entry
        """
        client = await self._get_client()
        now = datetime.utcnow()

        entry = DLQEntry(
            job_id=job_id,
            tenant_id=tenant_id,
            function_id=function_id,
            original_data=original_data,
            error=error,
            attempts=attempts,
            failed_at=now,
            metadata=metadata,
        )

        # Store entry data and add to sorted set (ordered by failure time)
        pipe = client.pipeline()
        pipe.set(self._entry_key(job_id), json.dumps(entry.to_dict()))
        pipe.zadd(self.dlq_key, {job_id: time.time()})
        await pipe.execute()

        self._log.warning(
            "job_moved_to_dlq",
            job_id=job_id,
            tenant_id=tenant_id,
            function_id=function_id,
            attempts=attempts,
            error=error[:200],  # Truncate long errors
        )

        return entry

    async def get(self, job_id: str) -> DLQEntry | None:
        """Get a specific DLQ entry by job ID."""
        client = await self._get_client()

        data = await client.get(self._entry_key(job_id))
        if not data:
            return None

        return DLQEntry.from_dict(json.loads(data))

    async def list(
        self,
        tenant_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DLQEntry]:
        """
        List DLQ entries.

        Args:
            tenant_id: Optional filter by tenant
            limit: Maximum entries to return
            offset: Number of entries to skip

        Returns:
            List of DLQ entries
        """
        client = await self._get_client()

        # Get job IDs from sorted set (newest first)
        job_ids = await client.zrevrange(self.dlq_key, offset, offset + limit - 1)

        entries = []
        for job_id in job_ids:
            data = await client.get(self._entry_key(job_id))
            if data:
                entry = DLQEntry.from_dict(json.loads(data))
                # Filter by tenant if specified
                if tenant_id is None or entry.tenant_id == tenant_id:
                    entries.append(entry)

        return entries

    async def count(self, tenant_id: str | None = None) -> int:
        """Count entries in the DLQ."""
        client = await self._get_client()

        if tenant_id is None:
            return await client.zcard(self.dlq_key)

        # Count with tenant filter (less efficient)
        entries = await self.list(tenant_id=tenant_id, limit=10000)
        return len(entries)

    async def remove(self, job_id: str) -> bool:
        """
        Remove an entry from the DLQ.

        Args:
            job_id: Job to remove

        Returns:
            True if removed, False if not found
        """
        client = await self._get_client()

        pipe = client.pipeline()
        pipe.delete(self._entry_key(job_id))
        pipe.zrem(self.dlq_key, job_id)
        results = await pipe.execute()

        removed = results[1] > 0

        if removed:
            self._log.info("job_removed_from_dlq", job_id=job_id)

        return removed

    async def requeue(self, job_id: str) -> bool:
        """
        Requeue a job from the DLQ back to the main queue.

        This removes the job from DLQ and returns the entry data
        so the caller can re-enqueue it.

        Args:
            job_id: Job to requeue

        Returns:
            True if successful, False if job not found
        """
        entry = await self.get(job_id)
        if not entry:
            return False

        # Remove from DLQ
        await self.remove(job_id)

        self._log.info(
            "job_requeued_from_dlq",
            job_id=job_id,
            tenant_id=entry.tenant_id,
            function_id=entry.function_id,
        )

        return True

    async def get_entry_for_requeue(self, job_id: str) -> DLQEntry | None:
        """
        Get a DLQ entry's data for requeuing.

        The caller is responsible for creating a new job from this data.
        """
        return await self.get(job_id)

    async def clear(self, tenant_id: str | None = None) -> int:
        """
        Clear entries from the DLQ.

        Args:
            tenant_id: If specified, only clear entries for this tenant

        Returns:
            Number of entries removed
        """
        client = await self._get_client()

        if tenant_id is None:
            # Clear all entries
            job_ids = await client.zrange(self.dlq_key, 0, -1)
            if not job_ids:
                return 0

            pipe = client.pipeline()
            for job_id in job_ids:
                pipe.delete(self._entry_key(job_id))
            pipe.delete(self.dlq_key)
            await pipe.execute()

            self._log.info("dlq_cleared", count=len(job_ids))
            return len(job_ids)

        # Clear only entries for specific tenant
        entries = await self.list(tenant_id=tenant_id, limit=10000)
        if not entries:
            return 0

        pipe = client.pipeline()
        for entry in entries:
            pipe.delete(self._entry_key(entry.job_id))
            pipe.zrem(self.dlq_key, entry.job_id)
        await pipe.execute()

        self._log.info("dlq_cleared_for_tenant", tenant_id=tenant_id, count=len(entries))
        return len(entries)

    async def get_stats(self) -> dict[str, Any]:
        """Get DLQ statistics."""
        client = await self._get_client()

        total = await client.zcard(self.dlq_key)

        # Get oldest and newest entry timestamps
        oldest = await client.zrange(self.dlq_key, 0, 0, withscores=True)
        newest = await client.zrevrange(self.dlq_key, 0, 0, withscores=True)

        return {
            "total": total,
            "oldest_at": datetime.fromtimestamp(oldest[0][1]).isoformat() if oldest else None,
            "newest_at": datetime.fromtimestamp(newest[0][1]).isoformat() if newest else None,
        }


# Global instance (lazy-initialized)
_dlq: DeadLetterQueue | None = None


async def get_dlq() -> DeadLetterQueue:
    """Get the global DLQ instance."""
    global _dlq
    if _dlq is None:
        _dlq = DeadLetterQueue()
    return _dlq
