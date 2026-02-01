"""Token rotation service for refresh tokens.

Implements refresh token rotation to prevent token replay attacks.
Once a refresh token is used, it cannot be used again.
"""

from __future__ import annotations

import redis.asyncio as redis

from flowforge_server.config import get_settings
from flowforge_server.logging import Loggers


class TokenRotationService:
    """
    Redis-based refresh token rotation tracking.

    When a refresh token is used, its JTI (unique ID) is stored in Redis.
    Subsequent attempts to use the same token are rejected.

    This prevents token replay attacks where an attacker captures
    and reuses a refresh token.
    """

    def __init__(
        self,
        redis_url: str | None = None,
        prefix: str = "flowforge:tokens",
    ) -> None:
        settings = get_settings()
        self.redis_url = redis_url or settings.redis_url
        self.prefix = prefix
        self._client: redis.Redis | None = None
        self._log = Loggers.api()

        # Token expiry padding (keep used tokens for slightly longer than refresh expiry)
        self.expiry_padding = 3600  # 1 hour extra

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

    def _used_token_key(self, jti: str) -> str:
        """Key for tracking used token JTIs."""
        return f"{self.prefix}:used:{jti}"

    def _user_tokens_key(self, user_id: str) -> str:
        """Key for tracking a user's active refresh tokens."""
        return f"{self.prefix}:user:{user_id}"

    async def mark_token_used(
        self,
        jti: str,
        user_id: str,
        expiry_seconds: int | None = None,
    ) -> bool:
        """
        Mark a refresh token as used.

        Args:
            jti: The token's unique ID (jti claim)
            user_id: The user who owns the token
            expiry_seconds: How long to remember this token was used

        Returns:
            True if this is the first use, False if already used
        """
        client = await self._get_client()
        settings = get_settings()

        if expiry_seconds is None:
            expiry_seconds = settings.jwt_refresh_expiry_seconds + self.expiry_padding

        key = self._used_token_key(jti)

        # Use SETNX to atomically check and set
        # Returns True if key was set (first use), False if already exists
        was_set = await client.setnx(key, user_id)

        if was_set:
            # Set expiry on the key
            await client.expire(key, expiry_seconds)
            self._log.debug("refresh_token_marked_used", jti=jti[:8] + "...", user_id=user_id)
        else:
            self._log.warning(
                "refresh_token_reuse_attempt",
                jti=jti[:8] + "...",
                user_id=user_id,
            )

        return was_set

    async def is_token_used(self, jti: str) -> bool:
        """
        Check if a refresh token has already been used.

        Args:
            jti: The token's unique ID

        Returns:
            True if token has been used, False otherwise
        """
        client = await self._get_client()
        key = self._used_token_key(jti)
        return await client.exists(key) > 0

    async def invalidate_user_tokens(self, user_id: str) -> int:
        """
        Invalidate all refresh tokens for a user.

        This is useful for:
        - Password changes
        - Forced logout
        - Account compromise

        Note: This sets a "revoked_at" timestamp. All tokens issued
        before this timestamp are considered invalid.

        Args:
            user_id: The user whose tokens should be invalidated

        Returns:
            Always returns 1 (the revocation marker was set)
        """
        client = await self._get_client()
        settings = get_settings()

        import time
        revoked_at = int(time.time())

        key = f"{self.prefix}:revoked:{user_id}"
        await client.set(key, str(revoked_at))
        # Keep revocation marker for refresh token lifetime
        await client.expire(key, settings.jwt_refresh_expiry_seconds + self.expiry_padding)

        self._log.info("user_tokens_invalidated", user_id=user_id, revoked_at=revoked_at)

        return 1

    async def is_user_token_revoked(self, user_id: str, issued_at: int) -> bool:
        """
        Check if a user's token was issued before their tokens were revoked.

        Args:
            user_id: The user ID from the token
            issued_at: The token's iat (issued at) timestamp

        Returns:
            True if token was revoked (issued before revocation), False otherwise
        """
        client = await self._get_client()

        key = f"{self.prefix}:revoked:{user_id}"
        revoked_at = await client.get(key)

        if revoked_at is None:
            return False

        return issued_at < int(revoked_at)


# Global instance (lazy-initialized)
_token_rotation_service: TokenRotationService | None = None


async def get_token_rotation_service() -> TokenRotationService:
    """Get the global token rotation service instance."""
    global _token_rotation_service
    if _token_rotation_service is None:
        _token_rotation_service = TokenRotationService()
    return _token_rotation_service
