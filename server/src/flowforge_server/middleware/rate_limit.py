"""Rate limiting and brute force protection middleware.

Provides Redis-based rate limiting with sliding window algorithm
and brute force protection with exponential backoff.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

import redis.asyncio as redis

from flowforge_server.config import get_settings
from flowforge_server.logging import Loggers

if TYPE_CHECKING:
    pass


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str,
        retry_after: int | None = None,
        limit: int | None = None,
        remaining: int = 0,
    ):
        super().__init__(message)
        self.retry_after = retry_after
        self.limit = limit
        self.remaining = remaining


@dataclass
class RateLimitInfo:
    """Rate limit status information."""

    allowed: bool
    limit: int
    remaining: int
    reset_at: int  # Unix timestamp
    retry_after: int | None = None  # Seconds until reset (only if not allowed)


class RateLimiter:
    """
    Redis-based sliding window rate limiter.

    Uses Redis sorted sets for efficient sliding window implementation.
    """

    def __init__(
        self,
        redis_url: str | None = None,
        prefix: str = "flowforge:ratelimit",
    ) -> None:
        settings = get_settings()
        self.redis_url = redis_url or settings.redis_url
        self.prefix = prefix
        self._client: redis.Redis | None = None
        self._log = Loggers.api()

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

    def _make_key(self, identifier: str, action: str) -> str:
        """Create a rate limit key."""
        return f"{self.prefix}:{action}:{identifier}"

    async def check_rate_limit(
        self,
        identifier: str,
        action: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitInfo:
        """
        Check if request is within rate limit using sliding window.

        Args:
            identifier: Unique identifier (IP, user ID, etc.)
            action: Action being rate limited (login, api, etc.)
            limit: Maximum requests allowed in window
            window_seconds: Time window in seconds

        Returns:
            RateLimitInfo with allowed status and metadata
        """
        client = await self._get_client()
        key = self._make_key(identifier, action)
        now = time.time()
        window_start = now - window_seconds

        # Use Redis pipeline for atomic operations
        pipe = client.pipeline()

        # Remove old entries outside the window
        pipe.zremrangebyscore(key, "-inf", window_start)

        # Count current entries in window
        pipe.zcard(key)

        # Get the oldest entry (for reset calculation)
        pipe.zrange(key, 0, 0, withscores=True)

        results = await pipe.execute()
        current_count = results[1]
        oldest_entry = results[2]

        # Calculate reset time
        if oldest_entry:
            oldest_time = oldest_entry[0][1]
            reset_at = int(oldest_time + window_seconds)
        else:
            reset_at = int(now + window_seconds)

        remaining = max(0, limit - current_count)
        allowed = current_count < limit

        if allowed:
            # Add this request to the window
            await client.zadd(key, {f"{now}": now})
            # Set expiry on the key
            await client.expire(key, window_seconds + 1)
            remaining = max(0, limit - current_count - 1)

        retry_after = None if allowed else max(1, reset_at - int(now))

        return RateLimitInfo(
            allowed=allowed,
            limit=limit,
            remaining=remaining,
            reset_at=reset_at,
            retry_after=retry_after,
        )

    async def is_allowed(
        self,
        identifier: str,
        action: str,
        limit: int,
        window_seconds: int,
    ) -> bool:
        """Simple check if request is allowed."""
        info = await self.check_rate_limit(identifier, action, limit, window_seconds)
        return info.allowed


class LoginRateLimiter:
    """
    Specialized rate limiter for login endpoints with brute force protection.

    Features:
    - Per-IP rate limiting
    - Per-email rate limiting
    - Combined IP+email tracking for targeted attacks
    - Exponential backoff on failures
    - Account lockout after threshold
    """

    def __init__(
        self,
        redis_url: str | None = None,
        prefix: str = "flowforge:login",
    ) -> None:
        settings = get_settings()
        self.redis_url = redis_url or settings.redis_url
        self.prefix = prefix
        self._client: redis.Redis | None = None
        self._log = Loggers.api()

        # Configuration (from settings or defaults)
        self.rate_limit_per_minute = getattr(settings, "login_rate_limit", 10)
        self.lockout_threshold = getattr(settings, "login_lockout_threshold", 5)
        self.lockout_duration = getattr(settings, "login_lockout_duration", 900)  # 15 min
        self.max_lockout_duration = 3600  # 1 hour max

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

    def _hash_email(self, email: str) -> str:
        """Hash email for privacy in Redis keys."""
        return hashlib.sha256(email.lower().encode()).hexdigest()[:16]

    def _ip_key(self, ip: str) -> str:
        """Key for IP-based rate limiting."""
        return f"{self.prefix}:ip:{ip}"

    def _email_key(self, email: str) -> str:
        """Key for email-based rate limiting."""
        return f"{self.prefix}:email:{self._hash_email(email)}"

    def _combined_key(self, ip: str, email: str) -> str:
        """Key for combined IP+email tracking."""
        return f"{self.prefix}:combo:{ip}:{self._hash_email(email)}"

    def _lockout_key(self, identifier: str) -> str:
        """Key for lockout tracking."""
        return f"{self.prefix}:lockout:{identifier}"

    def _failures_key(self, identifier: str) -> str:
        """Key for tracking failed attempts."""
        return f"{self.prefix}:failures:{identifier}"

    async def check_rate_limit(self, ip: str) -> RateLimitInfo:
        """
        Check if login request is within rate limit.

        Args:
            ip: Client IP address

        Returns:
            RateLimitInfo with allowed status
        """
        client = await self._get_client()
        key = self._ip_key(ip)
        now = time.time()
        window_seconds = 60  # 1 minute window

        pipe = client.pipeline()
        pipe.zremrangebyscore(key, "-inf", now - window_seconds)
        pipe.zcard(key)
        results = await pipe.execute()

        current_count = results[1]
        allowed = current_count < self.rate_limit_per_minute

        if allowed:
            await client.zadd(key, {f"{now}": now})
            await client.expire(key, window_seconds + 1)

        remaining = max(0, self.rate_limit_per_minute - current_count - (1 if allowed else 0))
        reset_at = int(now + window_seconds)

        return RateLimitInfo(
            allowed=allowed,
            limit=self.rate_limit_per_minute,
            remaining=remaining,
            reset_at=reset_at,
            retry_after=None if allowed else window_seconds,
        )

    async def is_locked_out(self, ip: str, email: str | None = None) -> tuple[bool, int | None]:
        """
        Check if IP or email is locked out.

        Args:
            ip: Client IP address
            email: Optional email being attempted

        Returns:
            Tuple of (is_locked, retry_after_seconds)
        """
        client = await self._get_client()

        # Check IP lockout
        ip_lockout = await client.get(self._lockout_key(ip))
        if ip_lockout:
            ttl = await client.ttl(self._lockout_key(ip))
            return True, max(1, ttl)

        # Check email lockout if provided
        if email:
            email_hash = self._hash_email(email)
            email_lockout = await client.get(self._lockout_key(email_hash))
            if email_lockout:
                ttl = await client.ttl(self._lockout_key(email_hash))
                return True, max(1, ttl)

        return False, None

    async def record_failure(self, ip: str, email: str | None = None) -> tuple[int, bool]:
        """
        Record a failed login attempt.

        Args:
            ip: Client IP address
            email: Optional email that was attempted

        Returns:
            Tuple of (failure_count, is_now_locked)
        """
        client = await self._get_client()
        now = time.time()

        # Track failures per IP
        ip_failures_key = self._failures_key(ip)
        pipe = client.pipeline()
        pipe.incr(ip_failures_key)
        pipe.expire(ip_failures_key, self.lockout_duration * 2)  # Keep longer than lockout
        results = await pipe.execute()
        ip_failure_count = results[0]

        # Also track per email if provided
        email_failure_count = 0
        if email:
            email_hash = self._hash_email(email)
            email_failures_key = self._failures_key(email_hash)
            pipe = client.pipeline()
            pipe.incr(email_failures_key)
            pipe.expire(email_failures_key, self.lockout_duration * 2)
            results = await pipe.execute()
            email_failure_count = results[0]

        # Check if we need to lock out
        max_failures = max(ip_failure_count, email_failure_count)
        is_locked = False

        if max_failures >= self.lockout_threshold:
            # Calculate lockout duration with exponential backoff
            # Each subsequent lockout doubles duration (capped at max)
            multiplier = max(1, max_failures // self.lockout_threshold)
            duration = min(self.lockout_duration * multiplier, self.max_lockout_duration)

            # Lock out the IP
            await client.setex(self._lockout_key(ip), duration, "1")

            # Lock out the email if provided
            if email:
                email_hash = self._hash_email(email)
                await client.setex(self._lockout_key(email_hash), duration, "1")

            is_locked = True

            self._log.warning(
                "login_lockout_triggered",
                ip=ip,
                email_hash=self._hash_email(email) if email else None,
                failure_count=max_failures,
                lockout_duration=duration,
            )

        return int(max_failures), is_locked

    async def record_success(self, ip: str, email: str) -> None:
        """
        Record a successful login and reset failure counters.

        Args:
            ip: Client IP address
            email: Email that successfully logged in
        """
        client = await self._get_client()
        email_hash = self._hash_email(email)

        # Clear failure counters
        await client.delete(
            self._failures_key(ip),
            self._failures_key(email_hash),
            self._lockout_key(ip),
            self._lockout_key(email_hash),
        )

    async def get_headers(self, info: RateLimitInfo) -> dict[str, str]:
        """
        Generate rate limit headers for response.

        Args:
            info: Rate limit info from check

        Returns:
            Dict of headers to add to response
        """
        headers = {
            "X-RateLimit-Limit": str(info.limit),
            "X-RateLimit-Remaining": str(info.remaining),
            "X-RateLimit-Reset": str(info.reset_at),
        }

        if info.retry_after:
            headers["Retry-After"] = str(info.retry_after)

        return headers


# Global instances (lazy-initialized)
_rate_limiter: RateLimiter | None = None
_login_rate_limiter: LoginRateLimiter | None = None


async def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


async def get_login_rate_limiter() -> LoginRateLimiter:
    """Get the global login rate limiter instance."""
    global _login_rate_limiter
    if _login_rate_limiter is None:
        _login_rate_limiter = LoginRateLimiter()
    return _login_rate_limiter
