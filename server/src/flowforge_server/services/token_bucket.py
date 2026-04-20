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

# Lua script for an atomic prune-sum-reserve cycle. Runs in a single Redis
# round-trip so two concurrent callers can't both observe "under limit" and
# overshoot the TPM cap.
#
#   KEYS[1] = bucket key (sorted set)
#   ARGV[1] = now                 (unix seconds, float as string)
#   ARGV[2] = window_start        (now - 60)
#   ARGV[3] = tokens_per_minute   (int)
#   ARGV[4] = estimated_tokens    (int)
#   ARGV[5] = reservation_member  ("<uuid>:<tokens>")
#   ARGV[6] = window_seconds      (int, for EXPIRE)
#
# Returns a list: {allowed (0|1), retry_after (string), used_tokens (int)}.
# retry_after is always encoded as a string so Lua→Redis→Python round-trips
# without precision loss; caller converts to float.
_CHECK_AND_RESERVE_LUA = """
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', ARGV[2])

local used = 0
local oldest_score
local members = redis.call('ZRANGE', KEYS[1], 0, -1, 'WITHSCORES')
for i = 1, #members, 2 do
    local member = members[i]
    local score = tonumber(members[i + 1])
    if not oldest_score or score < oldest_score then
        oldest_score = score
    end
    local colon = string.find(member, ':[^:]*$')
    if colon then
        local tokens = tonumber(string.sub(member, colon + 1))
        if tokens then
            used = used + tokens
        end
    end
end

local limit = tonumber(ARGV[3])
local estimated = tonumber(ARGV[4])
if used + estimated > limit then
    local retry_after
    if oldest_score then
        retry_after = (oldest_score + tonumber(ARGV[6])) - tonumber(ARGV[1])
        if retry_after < 1 then retry_after = 1 end
    else
        retry_after = tonumber(ARGV[6])
    end
    return {0, tostring(retry_after), used}
end

redis.call('ZADD', KEYS[1], ARGV[1], ARGV[5])
redis.call('EXPIRE', KEYS[1], ARGV[6] + 5)
return {1, '0', used + estimated}
"""


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

    Implementation: a single Lua script (prune-sum-reserve) runs atomically
    on Redis. Entries are a sorted set of ``{member: "<uuid>:<tokens>",
    score: <now>}``. Concurrent callers serialise through the script and
    cannot both reserve past the limit.

    Falls back to a non-atomic Python path only if a FakeRedis stub (tests)
    lacks ``eval``.
    """
    if tokens_per_minute <= 0:
        return True, 0.0

    key = _bucket_key(tenant_id, function_id, model, grouping_key)
    now = time.time()
    window_start = now - _WINDOW_SECONDS
    reservation_id = uuid.uuid4().hex
    member = f"{reservation_id}:{estimated_tokens}"

    try:
        raw = await client.eval(
            _CHECK_AND_RESERVE_LUA,
            1,
            key,
            str(now),
            str(window_start),
            str(tokens_per_minute),
            str(estimated_tokens),
            member,
            str(int(_WINDOW_SECONDS)),
        )
    except AttributeError:
        # Test stubs that don't implement `eval` (e.g. minimal FakeRedis)
        # fall through to the non-atomic Python path below.
        return await _check_and_reserve_fallback(
            client,
            key=key,
            now=now,
            window_start=window_start,
            tokens_per_minute=tokens_per_minute,
            estimated_tokens=estimated_tokens,
            member=member,
        )

    allowed_raw, retry_after_raw, _used = raw
    allowed = int(allowed_raw) == 1
    retry_after = 0.0 if allowed else float(retry_after_raw)
    return allowed, retry_after


async def _check_and_reserve_fallback(
    client: redis.Redis,
    *,
    key: str,
    now: float,
    window_start: float,
    tokens_per_minute: int,
    estimated_tokens: int,
    member: str,
) -> tuple[bool, float]:
    """Non-atomic fallback used only by test stubs without Lua support."""
    await client.zremrangebyscore(key, "-inf", window_start)
    entries = await client.zrange(key, 0, -1, withscores=True)
    used = 0
    oldest_score: float | None = None
    for m, score in entries:
        if oldest_score is None or score < oldest_score:
            oldest_score = score
        try:
            m_str = m if isinstance(m, str) else m.decode()
            _, token_str = m_str.rsplit(":", 1)
            used += int(token_str)
        except (ValueError, AttributeError):
            continue

    if used + estimated_tokens > tokens_per_minute:
        if oldest_score is None:
            retry_after = _WINDOW_SECONDS
        else:
            retry_after = max(1.0, (oldest_score + _WINDOW_SECONDS) - now)
        return False, retry_after

    await client.zadd(key, {member: now})
    await client.expire(key, int(_WINDOW_SECONDS) + 5)
    return True, 0.0
