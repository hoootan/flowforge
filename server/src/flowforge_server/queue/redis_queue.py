"""Redis-based queue implementation."""

import json
import random
import time
from datetime import datetime
from typing import Any

import redis.asyncio as redis

from flowforge_server.queue.base import Queue, Job, JobStatus
from flowforge_server.config import get_settings


class RedisQueue(Queue):
    """
    Redis-based queue implementation.

    Uses Redis sorted sets for priority queue and delayed jobs.
    Uses Redis hashes for job storage.
    """

    def __init__(
        self,
        redis_url: str | None = None,
        prefix: str = "flowforge",
    ) -> None:
        """
        Initialize Redis queue.

        Args:
            redis_url: Redis connection URL.
            prefix: Key prefix for all Redis keys.
        """
        settings = get_settings()
        self.redis_url = redis_url or settings.redis_url
        self.prefix = prefix

        self._client: redis.Redis | None = None

        # Key names
        self.pending_key = f"{prefix}:queue:pending"
        self.scheduled_key = f"{prefix}:queue:scheduled"
        self.running_key = f"{prefix}:queue:running"
        self.jobs_key = f"{prefix}:jobs"

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

    def _job_key(self, job_id: str) -> str:
        """Get the Redis key for a job."""
        return f"{self.jobs_key}:{job_id}"

    async def enqueue(
        self,
        job: Job,
        delay: float | None = None,
    ) -> str:
        """Add a job to the queue."""
        client = await self._get_client()

        # Store job data
        job_data = json.dumps(job.to_dict())
        await client.set(self._job_key(job.id), job_data)

        # Calculate score (timestamp for priority ordering)
        now = time.time()

        if delay and delay > 0:
            # Add to scheduled queue
            score = now + delay
            await client.zadd(self.scheduled_key, {job.id: score})
        else:
            # Add to pending queue with priority
            # Lower priority value = processed first
            # Within same priority, FIFO based on timestamp
            score = job.priority * 1_000_000_000 + now
            await client.zadd(self.pending_key, {job.id: score})

        return job.id

    async def dequeue(
        self,
        timeout: float = 0,
    ) -> Job | None:
        """Remove and return the next available job."""
        client = await self._get_client()

        # First, move any scheduled jobs that are due
        await self._process_scheduled()

        # Try to get a job from the pending queue
        start_time = time.time()

        while True:
            # Pop the job with lowest score (highest priority, oldest)
            result = await client.zpopmin(self.pending_key, count=1)

            if result:
                job_id = result[0][0]

                # Get job data
                job_data = await client.get(self._job_key(job_id))
                if job_data:
                    job = Job.from_dict(json.loads(job_data))
                    job.status = JobStatus.RUNNING
                    job.started_at = datetime.utcnow()

                    # Update job and add to running set
                    await client.set(self._job_key(job_id), json.dumps(job.to_dict()))
                    await client.sadd(self.running_key, job_id)

                    return job

            # Check timeout
            if timeout <= 0:
                return None

            elapsed = time.time() - start_time
            if elapsed >= timeout:
                return None

            # Wait a bit before retrying
            await client.ping()  # Keep connection alive
            import asyncio
            await asyncio.sleep(min(0.1, timeout - elapsed))

    async def _process_scheduled(self) -> int:
        """Move scheduled jobs that are due to the pending queue."""
        client = await self._get_client()
        now = time.time()

        # Get all scheduled jobs that are due
        due_jobs = await client.zrangebyscore(
            self.scheduled_key,
            min="-inf",
            max=now,
        )

        if not due_jobs:
            return 0

        # Move each to pending queue
        for job_id in due_jobs:
            # Get job data to get priority
            job_data = await client.get(self._job_key(job_id))
            if job_data:
                job = Job.from_dict(json.loads(job_data))
                job.status = JobStatus.PENDING

                # Calculate score for pending queue
                score = job.priority * 1_000_000_000 + now

                # Atomic move from scheduled to pending
                pipe = client.pipeline()
                pipe.zrem(self.scheduled_key, job_id)
                pipe.zadd(self.pending_key, {job_id: score})
                pipe.set(self._job_key(job_id), json.dumps(job.to_dict()))
                await pipe.execute()

        return len(due_jobs)

    async def complete(self, job_id: str, result: Any = None) -> None:
        """Mark a job as completed."""
        client = await self._get_client()

        # Get job data
        job_data = await client.get(self._job_key(job_id))
        if not job_data:
            return

        job = Job.from_dict(json.loads(job_data))
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.utcnow()

        # Update job and remove from running
        pipe = client.pipeline()
        pipe.set(self._job_key(job_id), json.dumps(job.to_dict()))
        pipe.srem(self.running_key, job_id)
        # Set TTL for completed jobs (keep for 24 hours)
        pipe.expire(self._job_key(job_id), 86400)
        await pipe.execute()

    async def fail(
        self,
        job_id: str,
        error: str,
        retry: bool = True,
    ) -> bool:
        """Mark a job as failed, optionally retrying."""
        client = await self._get_client()

        # Get job data
        job_data = await client.get(self._job_key(job_id))
        if not job_data:
            return False

        job = Job.from_dict(json.loads(job_data))
        job.error = error

        # Check if we should retry
        will_retry = retry and job.attempt < job.max_attempts

        if will_retry:
            # Increment attempt and re-queue with backoff
            job.attempt += 1
            job.status = JobStatus.RETRYING

            # Exponential backoff with jitter to prevent thundering herd
            # Base backoff: 2^attempt (2, 4, 8, 16, ...)
            # Jitter: multiply by random factor between 0.5 and 1.5
            # Cap at 5 minutes (300 seconds)
            base_backoff = 2 ** job.attempt
            jitter_factor = 0.5 + random.random()  # 0.5 to 1.5
            backoff = min(base_backoff * jitter_factor, 300)

            pipe = client.pipeline()
            pipe.set(self._job_key(job_id), json.dumps(job.to_dict()))
            pipe.srem(self.running_key, job_id)
            pipe.zadd(self.scheduled_key, {job_id: time.time() + backoff})
            await pipe.execute()
        else:
            # Mark as permanently failed
            job.status = JobStatus.FAILED
            job.completed_at = datetime.utcnow()

            pipe = client.pipeline()
            pipe.set(self._job_key(job_id), json.dumps(job.to_dict()))
            pipe.srem(self.running_key, job_id)
            # Keep failed jobs for 7 days
            pipe.expire(self._job_key(job_id), 604800)
            await pipe.execute()

        return will_retry

    async def get_job(self, job_id: str) -> Job | None:
        """Get a job by ID."""
        client = await self._get_client()

        job_data = await client.get(self._job_key(job_id))
        if not job_data:
            return None

        return Job.from_dict(json.loads(job_data))

    async def get_pending_count(self) -> int:
        """Get the number of pending jobs."""
        client = await self._get_client()
        return await client.zcard(self.pending_key)

    async def get_running_count(self) -> int:
        """Get the number of running jobs."""
        client = await self._get_client()
        return await client.scard(self.running_key)

    async def get_scheduled_count(self) -> int:
        """Get the number of scheduled jobs."""
        client = await self._get_client()
        return await client.zcard(self.scheduled_key)

    async def clear(self) -> None:
        """Clear all queues (for testing)."""
        client = await self._get_client()

        # Get all job keys
        keys = []
        async for key in client.scan_iter(f"{self.prefix}:*"):
            keys.append(key)

        if keys:
            await client.delete(*keys)
