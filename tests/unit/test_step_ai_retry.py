"""Tests for the SDK-side durable retry loop in step.ai / step.agent.

Validates AC1, AC2, AC3, AC5, AC7: the loop honours num_retries, parses
retry_after from the server's structured rate-limit signal, sleeps durably
via step.sleep between attempts, and raises a typed RateLimited when the
budget is exhausted.

Architectural note: the actual LLM call happens server-side. The SDK's
step.ai just yields a request via StepCompleted and, on replay, reads the
server's response through memoisation. So we simulate the server by
feeding completed_steps into StepManager and asserting the control-flow
exceptions (StepCompleted for attempts/sleeps, RateLimited on exhaustion).
"""

from __future__ import annotations

import random

import pytest
from flowforge.exceptions import (
    RateLimited,
    RetryableError,
    StepCompleted,
    StepFailed,
)
from flowforge.steps import StepManager, _hash_step_id, _resolve_num_retries, _retry_sleep


def _hash(step_id: str) -> str:
    return _hash_step_id(step_id)


def _rate_limited_result(retry_after: float = 1.0) -> dict:
    return {
        "__rate_limited": True,
        "__retry_after": retry_after,
        "__provider": "anthropic",
        "__model": "claude-sonnet-4-6",
        "__error": "test 429",
    }


def _success_result() -> dict:
    return {
        "content": "ok",
        "model": "claude-sonnet-4-6",
        "provider": "anthropic",
        "usage": {"total_tokens": 42},
        "finish_reason": "stop",
        "tool_calls": [],
    }


@pytest.mark.asyncio
async def test_first_call_yields_with_original_step_id() -> None:
    """With no memoised attempts, the first call yields StepCompleted for the
    plain step_id (no /attempt-N suffix — back-compat)."""
    mgr = StepManager(run_id="r1", completed_steps={})

    with pytest.raises(StepCompleted) as exc:
        await mgr.ai("think", model="claude-sonnet-4-6", prompt="hi", num_retries=3)

    assert exc.value.step_id == "think"
    assert exc.value.result["type"] == "ai"
    assert exc.value.result["model"] == "claude-sonnet-4-6"


@pytest.mark.asyncio
async def test_success_returns_memoised_response() -> None:
    """When the first-attempt step is memoised with a normal AI response, the
    loop returns it straight through."""
    completed = {_hash("think"): _success_result()}
    mgr = StepManager(run_id="r1", completed_steps=completed)

    result = await mgr.ai("think", model="claude-sonnet-4-6", prompt="hi", num_retries=3)

    assert result == _success_result()


@pytest.mark.asyncio
async def test_rate_limited_first_attempt_yields_sleep() -> None:
    """First attempt came back as __rate_limited; loop must yield a
    step.sleep for retry-sleep-1 and expose the step_id as such."""
    completed = {_hash("think"): _rate_limited_result(retry_after=5)}
    mgr = StepManager(run_id="r1", completed_steps=completed)

    random.seed(0)
    with pytest.raises(StepCompleted) as exc:
        await mgr.ai("think", model="claude-sonnet-4-6", prompt="hi", num_retries=3)

    assert exc.value.step_id == "think/retry-sleep-1"
    assert exc.value.result["type"] == "sleep"
    # 5s * jitter in [0.8, 1.2] = [4.0, 6.0], clamped to >= 1.0
    assert 4.0 <= exc.value.result["duration_seconds"] <= 6.0


@pytest.mark.asyncio
async def test_after_sleep_loop_yields_second_attempt() -> None:
    """Once attempt-1 and retry-sleep-1 are memoised, the loop should yield
    StepCompleted for attempt-2."""
    completed = {
        _hash("think"): _rate_limited_result(retry_after=5),
        _hash("think/retry-sleep-1"): None,
    }
    mgr = StepManager(run_id="r1", completed_steps=completed)

    with pytest.raises(StepCompleted) as exc:
        await mgr.ai("think", model="claude-sonnet-4-6", prompt="hi", num_retries=3)

    assert exc.value.step_id == "think/attempt-2"


@pytest.mark.asyncio
async def test_successful_retry_returns_real_response() -> None:
    """After a rate-limit + sleep, a successful attempt-2 returns its result."""
    completed = {
        _hash("think"): _rate_limited_result(retry_after=5),
        _hash("think/retry-sleep-1"): None,
        _hash("think/attempt-2"): _success_result(),
    }
    mgr = StepManager(run_id="r1", completed_steps=completed)

    result = await mgr.ai("think", model="claude-sonnet-4-6", prompt="hi", num_retries=3)
    assert result == _success_result()


@pytest.mark.asyncio
async def test_num_retries_zero_fails_immediately_with_typed_exception() -> None:
    """num_retries=0 plus a rate-limit signal must raise RateLimited on the
    first attempt — no sleep, no /attempt-N suffix."""
    completed = {_hash("think"): _rate_limited_result(retry_after=5)}
    mgr = StepManager(run_id="r1", completed_steps=completed)

    with pytest.raises(RateLimited) as exc:
        await mgr.ai("think", model="claude-sonnet-4-6", prompt="hi", num_retries=0)

    assert exc.value.retry_after == 5
    assert exc.value.provider == "anthropic"
    assert exc.value.model == "claude-sonnet-4-6"
    # AC5: existing StepFailed catchers must keep working.
    assert isinstance(exc.value, StepFailed)
    assert isinstance(exc.value, RetryableError)


@pytest.mark.asyncio
async def test_exhausted_retries_raise_rate_limited() -> None:
    """All N+1 attempts rate-limited → RateLimited raised."""
    completed = {
        _hash("think"): _rate_limited_result(retry_after=1),
        _hash("think/retry-sleep-1"): None,
        _hash("think/attempt-2"): _rate_limited_result(retry_after=1),
        _hash("think/retry-sleep-2"): None,
        _hash("think/attempt-3"): _rate_limited_result(retry_after=1),
    }
    mgr = StepManager(run_id="r1", completed_steps=completed)

    with pytest.raises(RateLimited) as exc:
        await mgr.ai("think", model="claude-sonnet-4-6", prompt="hi", num_retries=2)

    assert exc.value.attempt == 3  # num_retries + 1


def test_resolve_num_retries_explicit_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FLOWFORGE_LLM_NUM_RETRIES", "9")
    assert _resolve_num_retries(2) == 2


def test_resolve_num_retries_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FLOWFORGE_LLM_NUM_RETRIES", "7")
    monkeypatch.delenv("LITELLM_NUM_RETRIES", raising=False)
    assert _resolve_num_retries(None) == 7


def test_resolve_num_retries_litellm_env_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FLOWFORGE_LLM_NUM_RETRIES", raising=False)
    monkeypatch.setenv("LITELLM_NUM_RETRIES", "4")
    assert _resolve_num_retries(None) == 4


def test_resolve_num_retries_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FLOWFORGE_LLM_NUM_RETRIES", raising=False)
    monkeypatch.delenv("LITELLM_NUM_RETRIES", raising=False)
    assert _resolve_num_retries(None) == 5


def test_resolve_num_retries_clamp_negative() -> None:
    assert _resolve_num_retries(-3) == 0


def test_retry_sleep_jitter_range(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sleep must be within ±20% of retry_after and >= 1s."""
    monkeypatch.delenv("FLOWFORGE_LLM_MAX_RETRY_DELAY", raising=False)
    for _ in range(100):
        s = _retry_sleep(10.0)
        assert 8.0 <= s <= 12.0


def test_retry_sleep_minimum_floor() -> None:
    """Tiny retry_after gets clamped up to 1s so we don't hot-loop."""
    for _ in range(20):
        assert _retry_sleep(0.1) >= 1.0


def test_retry_sleep_max_delay_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    """Very large retry_after gets clamped by FLOWFORGE_LLM_MAX_RETRY_DELAY."""
    monkeypatch.setenv("FLOWFORGE_LLM_MAX_RETRY_DELAY", "30")
    for _ in range(20):
        assert _retry_sleep(1000.0) <= 30.0
