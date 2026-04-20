"""Unit tests for the AI token-bucket pre-flight throttler.

Validates AC9: declarative per-model TPM limits absorb back-pressure before
a request reaches the provider. Exhaustion returns (False, retry_after_s) so
the SDK's step.ai loop can sleep durably and try again.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from flowforge_server.services.token_bucket import check_and_reserve


class _FakeRedis:
    """In-memory stand-in for redis.Redis exposing just what check_and_reserve uses."""

    def __init__(self) -> None:
        self.zsets: dict[str, list[tuple[str, float]]] = {}
        self.expirations: dict[str, int] = {}

    async def zremrangebyscore(self, key: str, min_score, max_score) -> int:
        items = self.zsets.get(key, [])
        self.zsets[key] = [
            (m, s) for m, s in items if not (float(min_score) <= s <= float(max_score))
        ]
        return 0

    async def zrange(self, key: str, start: int, stop: int, withscores: bool = False):
        items = sorted(self.zsets.get(key, []), key=lambda x: x[1])
        slice_ = items if stop == -1 else items[start : stop + 1]
        return list(slice_) if withscores else [m for m, _ in slice_]

    async def zadd(self, key: str, mapping: dict[str, float]) -> int:
        self.zsets.setdefault(key, [])
        for member, score in mapping.items():
            self.zsets[key].append((member, float(score)))
        return len(mapping)

    async def expire(self, key: str, seconds: int) -> int:
        self.expirations[key] = seconds
        return 1


@pytest.mark.asyncio
async def test_bucket_allows_under_limit() -> None:
    r = _FakeRedis()
    allowed, wait = await check_and_reserve(
        r,  # type: ignore[arg-type]
        tenant_id="t",
        function_id="f",
        model="claude-sonnet-4-6",
        estimated_tokens=500,
        tokens_per_minute=10_000,
    )
    assert allowed is True
    assert wait == 0.0


@pytest.mark.asyncio
async def test_bucket_rejects_over_limit() -> None:
    r = _FakeRedis()
    await check_and_reserve(
        r,  # type: ignore[arg-type]
        tenant_id="t",
        function_id="f",
        model="claude-sonnet-4-6",
        estimated_tokens=8000,
        tokens_per_minute=10_000,
    )
    allowed, wait = await check_and_reserve(
        r,  # type: ignore[arg-type]
        tenant_id="t",
        function_id="f",
        model="claude-sonnet-4-6",
        estimated_tokens=5000,
        tokens_per_minute=10_000,
    )
    assert allowed is False
    # Until the oldest reservation ages out (just made — almost a full 60s)
    assert 50.0 <= wait <= 60.0


@pytest.mark.asyncio
async def test_bucket_isolates_models() -> None:
    """Two different models share no state."""
    r = _FakeRedis()
    await check_and_reserve(
        r,  # type: ignore[arg-type]
        tenant_id="t",
        function_id="f",
        model="claude-sonnet-4-6",
        estimated_tokens=10_000,
        tokens_per_minute=10_000,
    )
    allowed, _ = await check_and_reserve(
        r,  # type: ignore[arg-type]
        tenant_id="t",
        function_id="f",
        model="gpt-5.3",
        estimated_tokens=9_000,
        tokens_per_minute=10_000,
    )
    assert allowed is True


@pytest.mark.asyncio
async def test_bucket_grouping_key_splits_buckets() -> None:
    """Same model but different grouping keys → separate buckets."""
    r = _FakeRedis()
    await check_and_reserve(
        r,  # type: ignore[arg-type]
        tenant_id="t",
        function_id="f",
        model="claude-sonnet-4-6",
        estimated_tokens=10_000,
        tokens_per_minute=10_000,
        grouping_key="tenant-A",
    )
    allowed, _ = await check_and_reserve(
        r,  # type: ignore[arg-type]
        tenant_id="t",
        function_id="f",
        model="claude-sonnet-4-6",
        estimated_tokens=9_000,
        tokens_per_minute=10_000,
        grouping_key="tenant-B",
    )
    assert allowed is True


@pytest.mark.asyncio
async def test_bucket_zero_limit_is_no_op() -> None:
    """tokens_per_minute=0 disables the check (treated as unconfigured)."""
    r = _FakeRedis()
    allowed, _ = await check_and_reserve(
        r,  # type: ignore[arg-type]
        tenant_id="t",
        function_id="f",
        model="claude-sonnet-4-6",
        estimated_tokens=1_000_000,
        tokens_per_minute=0,
    )
    assert allowed is True
