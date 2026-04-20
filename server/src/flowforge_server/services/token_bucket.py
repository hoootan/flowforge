"""
Redis-backed sliding-window token bucket for LLM pre-flight throttling.

Used by `AIService.complete()` to absorb back-pressure from provider TPM
caps *before* a request goes out. When a caller declares
`rate_limits=[TokenRateLimit(model, tokens_per_minute=N)]` on a function,
the bucket refuses requests that would exceed N tokens in any rolling 60s
window — surfaced as a structured `__rate_limited` signal so the SDK's
durable retry loop can sleep via `step.sleep` instead of hammering the
provider.

Proactive throttling > reactive 429 handling (Anthropic guidance).
"""

from __future__ import annotations

import time
import uuid

import redis.asyncio as redis

_WINDOW_SECONDS = 60.0
_KEY_PREFIX = "flowforge:tokenbucket"


def _bucket_key(
    tenant_id: str | uuid.UUID,
    function_id: str,
    model: str,
    grouping_key: str | None = None,
) -> str:
    key = f"{_KEY_PREFIX}:{tenant_id}:{function_id}:{model}"
    if grouping_key:
        key = f"{key}:{grouping_key}"
    return key


async def check_and_reserve(
    client: redis.Redis,
    *,
    tenant_id: str | uuid.UUID,
    function_id: str,
    model: str,
    estimated_tokens: int,
    tokens_per_minute: int,
    grouping_key: str | None = None,
) -> tuple[bool, float]:
    """
    Try to reserve `estimated_tokens` from the per-model-per-minute bucket.

    Returns `(allowed, retry_after_seconds)`:
      - (True, 0.0) — reservation made; request may proceed.
      - (False, s)  — would exceed limit; caller must wait `s` seconds then
                      retry. `s` is the time until the oldest reservation in
                      the window expires and frees enough capacity.

    Implementation: sliding 60s window on a Redis sorted set where each entry
    is `{member: "<uuid>:<tokens>", score: <now>}`. Expired entries are pruned
    atomically; current usage is the sum of live entries' token counts.

    Accuracy trade-off: two concurrent callers can briefly both observe
    "under limit" and both reserve, transiently overshooting by up to one
    request's estimated size. Acceptable for provider-tier back-pressure;
    the worst case is a single 429 the durable retry loop absorbs.
    """
    if tokens_per_minute <= 0:
        return True, 0.0

    key = _bucket_key(tenant_id, function_id, model, grouping_key)
    now = time.time()
    window_start = now - _WINDOW_SECONDS

    # Prune expired entries first.
    await client.zremrangebyscore(key, "-inf", window_start)

    # Sum the tokens currently held in the window.
    entries = await client.zrange(key, 0, -1, withscores=True)
    used = 0
    oldest_score: float | None = None
    for member, score in entries:
        if oldest_score is None or score < oldest_score:
            oldest_score = score
        # Member format: "<id>:<tokens>". Fall back to 0 on parse errors so
        # stale entries from older schemas don't poison the bucket.
        try:
            member_str = member if isinstance(member, str) else member.decode()
            _, token_str = member_str.rsplit(":", 1)
            used += int(token_str)
        except (ValueError, AttributeError):
            continue

    if used + estimated_tokens > tokens_per_minute:
        if oldest_score is None:
            retry_after = _WINDOW_SECONDS
        else:
            retry_after = max(1.0, (oldest_score + _WINDOW_SECONDS) - now)
        return False, retry_after

    # Reserve.
    reservation_id = uuid.uuid4().hex
    member = f"{reservation_id}:{estimated_tokens}"
    await client.zadd(key, {member: now})
    await client.expire(key, int(_WINDOW_SECONDS) + 5)
    return True, 0.0
