"""Flow control for concurrency, rate limiting, and throttling."""

from dataclasses import dataclass
from typing import Any
import time

import redis.asyncio as redis

from flowforge_server.config import get_settings


@dataclass
class FlowControlConfig:
    """Configuration for flow control."""

    # Concurrency
    concurrency_limit: int | None = None
    concurrency_key: str | None = None  # Expression for per-key limiting

    # Rate limiting
    rate_limit: int | None = None
    rate_period_seconds: int = 60
    rate_key: str | None = None

    # Throttle
    throttle_limit: int | None = None
    throttle_period_seconds: int = 1
    throttle_key: str | None = None

    @classmethod
    def from_function_config(cls, config: dict[str, Any]) -> "FlowControlConfig":
        """Create from function configuration."""
        fc = cls()

        if "concurrency" in config:
            cc = config["concurrency"]
            fc.concurrency_limit = cc.get("limit")
            fc.concurrency_key = cc.get("key")

        if "rate_limit" in config:
            rl = config["rate_limit"]
            fc.rate_limit = rl.get("limit")
            fc.rate_period_seconds = cls._parse_period(rl.get("period", "1m"))
            fc.rate_key = rl.get("key")

        if "throttle" in config:
            th = config["throttle"]
            fc.throttle_limit = th.get("limit")
            fc.throttle_period_seconds = cls._parse_period(th.get("period", "1s"))
            fc.throttle_key = th.get("key")

        return fc

    @staticmethod
    def _parse_period(period: str) -> int:
        """Parse a period string like '1m', '1h', '30s' to seconds."""
        period = period.strip().lower()
        units = {
            "s": 1,
            "m": 60,
            "h": 3600,
            "d": 86400,
        }

        for unit, multiplier in units.items():
            if period.endswith(unit):
                try:
                    return int(period[:-1]) * multiplier
                except ValueError:
                    pass

        # Try parsing as raw seconds
        try:
            return int(period)
        except ValueError:
            return 60  # Default to 1 minute


class FlowController:
    """
    Flow control manager for concurrency and rate limiting.

    Provides:
    - Per-function concurrency limits
    - Per-function rate limits
    - Per-key variants for all limits
    - Throttling
    """

    def __init__(self, redis_url: str | None = None, prefix: str = "flowforge") -> None:
        settings = get_settings()
        self.redis_url = redis_url or settings.redis_url
        self.prefix = prefix

        self._client: redis.Redis | None = None

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

    def _concurrency_key(self, function_id: str, key: str | None = None) -> str:
        """Get Redis key for concurrency tracking."""
        if key:
            return f"{self.prefix}:concurrency:{function_id}:{key}"
        return f"{self.prefix}:concurrency:{function_id}"

    def _rate_limit_key(self, function_id: str, key: str | None = None) -> str:
        """Get Redis key for rate limiting."""
        if key:
            return f"{self.prefix}:ratelimit:{function_id}:{key}"
        return f"{self.prefix}:ratelimit:{function_id}"

    def _throttle_key(self, function_id: str, key: str | None = None) -> str:
        """Get Redis key for throttling."""
        if key:
            return f"{self.prefix}:throttle:{function_id}:{key}"
        return f"{self.prefix}:throttle:{function_id}"

    async def acquire_concurrency(
        self,
        function_id: str,
        job_id: str,
        limit: int,
        key: str | None = None,
    ) -> bool:
        """
        Acquire a concurrency slot.

        Args:
            function_id: Function identifier.
            job_id: Job identifier to track.
            limit: Maximum concurrent jobs.
            key: Optional per-key limit identifier.

        Returns:
            True if slot acquired, False if at limit.
        """
        client = await self._get_client()
        redis_key = self._concurrency_key(function_id, key)

        # Check current count
        current = await client.scard(redis_key)
        if current >= limit:
            return False

        # Add to set
        await client.sadd(redis_key, job_id)
        return True

    async def release_concurrency(
        self,
        function_id: str,
        job_id: str,
        key: str | None = None,
    ) -> None:
        """Release a concurrency slot."""
        client = await self._get_client()
        redis_key = self._concurrency_key(function_id, key)
        await client.srem(redis_key, job_id)

    async def get_concurrency_count(
        self,
        function_id: str,
        key: str | None = None,
    ) -> int:
        """Get current concurrency count."""
        client = await self._get_client()
        redis_key = self._concurrency_key(function_id, key)
        return await client.scard(redis_key)

    async def check_rate_limit(
        self,
        function_id: str,
        limit: int,
        period_seconds: int,
        key: str | None = None,
    ) -> tuple[bool, int]:
        """
        Check and update rate limit.

        Uses sliding window algorithm.

        Args:
            function_id: Function identifier.
            limit: Maximum requests in period.
            period_seconds: Time window in seconds.
            key: Optional per-key limit identifier.

        Returns:
            Tuple of (allowed, current_count).
        """
        client = await self._get_client()
        redis_key = self._rate_limit_key(function_id, key)
        now = time.time()
        window_start = now - period_seconds

        # Remove old entries
        await client.zremrangebyscore(redis_key, "-inf", window_start)

        # Get current count
        current = await client.zcard(redis_key)

        if current >= limit:
            return False, current

        # Add new entry
        await client.zadd(redis_key, {str(now): now})
        await client.expire(redis_key, period_seconds * 2)

        return True, current + 1

    async def check_throttle(
        self,
        function_id: str,
        limit: int,
        period_seconds: int,
        key: str | None = None,
    ) -> tuple[bool, float]:
        """
        Check throttle (minimum time between requests).

        Args:
            function_id: Function identifier.
            limit: Maximum requests in period.
            period_seconds: Time window in seconds.
            key: Optional per-key limit identifier.

        Returns:
            Tuple of (allowed, wait_time_seconds).
        """
        client = await self._get_client()
        redis_key = self._throttle_key(function_id, key)
        now = time.time()

        # Get last execution time
        last = await client.get(redis_key)

        if last:
            last_time = float(last)
            min_interval = period_seconds / limit
            time_since_last = now - last_time

            if time_since_last < min_interval:
                return False, min_interval - time_since_last

        # Update last execution time
        await client.set(redis_key, str(now), ex=period_seconds * 2)

        return True, 0

    async def can_execute(
        self,
        function_id: str,
        job_id: str,
        config: FlowControlConfig,
        key_values: dict[str, str] | None = None,
    ) -> tuple[bool, str | None]:
        """
        Check if a job can execute based on flow control config.

        Args:
            function_id: Function identifier.
            job_id: Job identifier.
            config: Flow control configuration.
            key_values: Optional key values for per-key limits.

        Returns:
            Tuple of (allowed, reason if not allowed).
        """
        # Check concurrency
        if config.concurrency_limit:
            key = key_values.get(config.concurrency_key) if key_values and config.concurrency_key else None
            if not await self.acquire_concurrency(function_id, job_id, config.concurrency_limit, key):
                return False, "concurrency_limit"

        # Check rate limit
        if config.rate_limit:
            key = key_values.get(config.rate_key) if key_values and config.rate_key else None
            allowed, _ = await self.check_rate_limit(
                function_id,
                config.rate_limit,
                config.rate_period_seconds,
                key,
            )
            if not allowed:
                # Release concurrency slot if we acquired one
                if config.concurrency_limit:
                    await self.release_concurrency(function_id, job_id)
                return False, "rate_limit"

        # Check throttle
        if config.throttle_limit:
            key = key_values.get(config.throttle_key) if key_values and config.throttle_key else None
            allowed, _ = await self.check_throttle(
                function_id,
                config.throttle_limit,
                config.throttle_period_seconds,
                key,
            )
            if not allowed:
                # Release concurrency slot if we acquired one
                if config.concurrency_limit:
                    await self.release_concurrency(function_id, job_id)
                return False, "throttle"

        return True, None

    async def release(
        self,
        function_id: str,
        job_id: str,
        config: FlowControlConfig,
        key_values: dict[str, str] | None = None,
    ) -> None:
        """Release all acquired flow control resources."""
        if config.concurrency_limit:
            key = key_values.get(config.concurrency_key) if key_values and config.concurrency_key else None
            await self.release_concurrency(function_id, job_id, key)
