"""Fair multi-tenant queue implementation."""

import json
import time
from datetime import datetime
from typing import Any

import redis.asyncio as redis

from flowforge_server.queue.base import Queue, Job, JobStatus
from flowforge_server.config import get_settings


# Lua script for fair dequeue across tenants
FAIR_DEQUEUE_SCRIPT = """
-- Get all active tenant queues
local tenant_queues = redis.call('SMEMBERS', KEYS[1])
if #tenant_queues == 0 then
    return nil
end

-- Get current round-robin index
local rr_idx = tonumber(redis.call('GET', KEYS[2]) or 0)
local now = tonumber(ARGV[1])

-- Try each tenant in round-robin order
for i = 1, #tenant_queues do
    local idx = ((rr_idx + i - 1) % #tenant_queues) + 1
    local queue_key = tenant_queues[idx]

    -- Get job with lowest score that's ready (score <= now)
    local jobs = redis.call('ZRANGEBYSCORE', queue_key, '-inf', now, 'LIMIT', 0, 1)

    if #jobs > 0 then
        local job_id = jobs[1]

        -- Remove from queue
        redis.call('ZREM', queue_key, job_id)

        -- Update round-robin index
        redis.call('SET', KEYS[2], idx)

        -- Check if queue is now empty
        if redis.call('ZCARD', queue_key) == 0 then
            redis.call('SREM', KEYS[1], queue_key)
        end

        return job_id
    end
end

-- Increment index for next attempt
redis.call('INCR', KEYS[2])
return nil
"""

# Lua script for checking concurrency limits
CHECK_CONCURRENCY_SCRIPT = """
local running_key = KEYS[1]
local limit = tonumber(ARGV[1])
local function_id = ARGV[2]

local current = redis.call('SCARD', running_key)
if current >= limit then
    return 0
end

redis.call('SADD', running_key, function_id)
return 1
"""


class FairQueue(Queue):
    """
    Fair multi-tenant queue with flow control.

    Features:
    - Round-robin scheduling across tenants
    - Per-function concurrency limits
    - Rate limiting
    - Priority support
    - Delayed/scheduled jobs
    """

    def __init__(
        self,
        redis_url: str | None = None,
        prefix: str = "flowforge",
    ) -> None:
        """
        Initialize fair queue.

        Args:
            redis_url: Redis connection URL.
            prefix: Key prefix for all Redis keys.
        """
        settings = get_settings()
        self.redis_url = redis_url or settings.redis_url
        self.prefix = prefix

        self._client: redis.Redis | None = None
        self._fair_dequeue_sha: str | None = None
        self._check_concurrency_sha: str | None = None

        # Key names
        self.active_tenants_key = f"{prefix}:fair:tenants"
        self.rr_index_key = f"{prefix}:fair:rr_index"
        self.scheduled_key = f"{prefix}:fair:scheduled"
        self.running_key = f"{prefix}:fair:running"
        self.jobs_key = f"{prefix}:jobs"
        self.concurrency_key_prefix = f"{prefix}:concurrency"
        self.rate_limit_key_prefix = f"{prefix}:ratelimit"

    async def _get_client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self._client is None:
            self._client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )

            # Register Lua scripts
            self._fair_dequeue_sha = await self._client.script_load(
                FAIR_DEQUEUE_SCRIPT
            )
            self._check_concurrency_sha = await self._client.script_load(
                CHECK_CONCURRENCY_SCRIPT
            )

        return self._client

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _tenant_queue_key(self, tenant_id: str) -> str:
        """Get the queue key for a tenant."""
        return f"{self.prefix}:fair:queue:{tenant_id}"

    def _job_key(self, job_id: str) -> str:
        """Get the Redis key for a job."""
        return f"{self.jobs_key}:{job_id}"

    def _concurrency_key(self, function_id: str) -> str:
        """Get the concurrency tracking key for a function."""
        return f"{self.concurrency_key_prefix}:{function_id}"

    def _rate_limit_key(self, function_id: str) -> str:
        """Get the rate limit key for a function."""
        return f"{self.rate_limit_key_prefix}:{function_id}"

    async def enqueue(
        self,
        job: Job,
        delay: float | None = None,
    ) -> str:
        """Add a job to the queue."""
        client = await self._get_client()
        now = time.time()

        # Store job data
        job_data = json.dumps(job.to_dict())
        await client.set(self._job_key(job.id), job_data)

        # Calculate score
        if delay and delay > 0:
            # Add to scheduled queue
            score = now + delay
            job.scheduled_at = datetime.fromtimestamp(score)
            job.status = JobStatus.SCHEDULED

            await client.set(self._job_key(job.id), json.dumps(job.to_dict()))
            await client.zadd(self.scheduled_key, {job.id: score})
        else:
            # Add to tenant's queue
            # Score = priority * 1B + timestamp (for FIFO within priority)
            score = job.priority * 1_000_000_000 + now

            tenant_queue = self._tenant_queue_key(job.tenant_id)

            pipe = client.pipeline()
            pipe.zadd(tenant_queue, {job.id: score})
            pipe.sadd(self.active_tenants_key, tenant_queue)
            await pipe.execute()

        return job.id

    async def dequeue(
        self,
        timeout: float = 0,
    ) -> Job | None:
        """Remove and return the next available job using fair scheduling."""
        client = await self._get_client()

        # First, move any scheduled jobs that are due
        await self._process_scheduled()

        start_time = time.time()
        now = time.time()

        while True:
            # Use Lua script for atomic fair dequeue
            try:
                job_id = await client.evalsha(
                    self._fair_dequeue_sha,
                    2,  # Number of keys
                    self.active_tenants_key,
                    self.rr_index_key,
                    str(now),  # Current timestamp
                )
            except redis.ResponseError:
                # Script not loaded, reload it
                self._fair_dequeue_sha = await client.script_load(
                    FAIR_DEQUEUE_SCRIPT
                )
                continue

            if job_id:
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

            # Wait before retrying
            import asyncio
            await asyncio.sleep(min(0.1, timeout - elapsed))
            now = time.time()

    async def _process_scheduled(self) -> int:
        """Move scheduled jobs that are due to tenant queues."""
        client = await self._get_client()
        now = time.time()

        # Get all scheduled jobs that are due
        due_jobs = await client.zrangebyscore(
            self.scheduled_key,
            min="-inf",
            max=now,
            start=0,
            num=100,  # Process in batches
        )

        if not due_jobs:
            return 0

        count = 0
        for job_id in due_jobs:
            job_data = await client.get(self._job_key(job_id))
            if job_data:
                job = Job.from_dict(json.loads(job_data))
                job.status = JobStatus.PENDING

                # Calculate score for tenant queue
                score = job.priority * 1_000_000_000 + now
                tenant_queue = self._tenant_queue_key(job.tenant_id)

                # Atomic move
                pipe = client.pipeline()
                pipe.zrem(self.scheduled_key, job_id)
                pipe.zadd(tenant_queue, {job_id: score})
                pipe.sadd(self.active_tenants_key, tenant_queue)
                pipe.set(self._job_key(job_id), json.dumps(job.to_dict()))
                await pipe.execute()

                count += 1

        return count

    async def complete(self, job_id: str, result: Any = None) -> None:
        """Mark a job as completed."""
        client = await self._get_client()

        job_data = await client.get(self._job_key(job_id))
        if not job_data:
            return

        job = Job.from_dict(json.loads(job_data))
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.utcnow()

        # Release concurrency slot
        concurrency_key = self._concurrency_key(job.function_id)

        pipe = client.pipeline()
        pipe.set(self._job_key(job_id), json.dumps(job.to_dict()))
        pipe.srem(self.running_key, job_id)
        pipe.srem(concurrency_key, job_id)
        pipe.expire(self._job_key(job_id), 86400)  # Keep for 24 hours
        await pipe.execute()

    async def fail(
        self,
        job_id: str,
        error: str,
        retry: bool = True,
    ) -> bool:
        """Mark a job as failed, optionally retrying."""
        client = await self._get_client()

        job_data = await client.get(self._job_key(job_id))
        if not job_data:
            return False

        job = Job.from_dict(json.loads(job_data))
        job.error = error

        # Release concurrency slot
        concurrency_key = self._concurrency_key(job.function_id)

        will_retry = retry and job.attempt < job.max_attempts

        if will_retry:
            job.attempt += 1
            job.status = JobStatus.RETRYING

            # Exponential backoff
            backoff = min(2 ** job.attempt, 300)

            pipe = client.pipeline()
            pipe.set(self._job_key(job_id), json.dumps(job.to_dict()))
            pipe.srem(self.running_key, job_id)
            pipe.srem(concurrency_key, job_id)
            pipe.zadd(self.scheduled_key, {job_id: time.time() + backoff})
            await pipe.execute()
        else:
            job.status = JobStatus.FAILED
            job.completed_at = datetime.utcnow()

            pipe = client.pipeline()
            pipe.set(self._job_key(job_id), json.dumps(job.to_dict()))
            pipe.srem(self.running_key, job_id)
            pipe.srem(concurrency_key, job_id)
            pipe.expire(self._job_key(job_id), 604800)  # Keep for 7 days
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
        """Get the number of pending jobs across all tenants."""
        client = await self._get_client()

        tenant_queues = await client.smembers(self.active_tenants_key)
        total = 0

        for queue_key in tenant_queues:
            count = await client.zcard(queue_key)
            total += count

        return total

    async def get_running_count(self) -> int:
        """Get the number of running jobs."""
        client = await self._get_client()
        return await client.scard(self.running_key)

    async def get_scheduled_count(self) -> int:
        """Get the number of scheduled jobs."""
        client = await self._get_client()
        return await client.zcard(self.scheduled_key)

    async def check_concurrency(
        self,
        function_id: str,
        limit: int,
        job_id: str,
    ) -> bool:
        """
        Check if we can run a job within concurrency limits.

        Args:
            function_id: Function ID to check.
            limit: Maximum concurrent executions.
            job_id: Job ID to add if allowed.

        Returns:
            True if job can run, False if at limit.
        """
        client = await self._get_client()
        concurrency_key = self._concurrency_key(function_id)

        current = await client.scard(concurrency_key)
        if current >= limit:
            return False

        await client.sadd(concurrency_key, job_id)
        return True

    async def release_concurrency(self, function_id: str, job_id: str) -> None:
        """Release a concurrency slot."""
        client = await self._get_client()
        concurrency_key = self._concurrency_key(function_id)
        await client.srem(concurrency_key, job_id)

    async def check_rate_limit(
        self,
        function_id: str,
        limit: int,
        period_seconds: int,
    ) -> bool:
        """
        Check if we're within rate limits.

        Uses sliding window rate limiting.

        Args:
            function_id: Function ID to check.
            limit: Maximum requests in period.
            period_seconds: Time period in seconds.

        Returns:
            True if within limits, False if rate limited.
        """
        client = await self._get_client()
        rate_key = self._rate_limit_key(function_id)
        now = time.time()
        window_start = now - period_seconds

        # Remove old entries and count current
        pipe = client.pipeline()
        pipe.zremrangebyscore(rate_key, "-inf", window_start)
        pipe.zcard(rate_key)
        results = await pipe.execute()

        current_count = results[1]

        if current_count >= limit:
            return False

        # Add current request
        await client.zadd(rate_key, {str(now): now})
        await client.expire(rate_key, period_seconds * 2)

        return True

    async def get_queue_stats(self) -> dict[str, Any]:
        """Get queue statistics."""
        return {
            "pending": await self.get_pending_count(),
            "running": await self.get_running_count(),
            "scheduled": await self.get_scheduled_count(),
        }
