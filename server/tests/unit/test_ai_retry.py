"""Tests for AIService rate-limit handling.

Confirms the server returns a structured `__rate_limited` payload instead
of raising on 429, so the SDK's durable retry loop can drive the wait via
step.sleep. Non-rate-limit errors still propagate unchanged.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from flowforge_server.services.ai import (
    AIResponse,
    AIService,
    _estimate_prompt_tokens,
    _is_rate_limit_error,
    _parse_retry_after,
)


class _FakeRateLimitError(Exception):
    """Stand-in for litellm.RateLimitError — duck-typed by status_code."""

    status_code = 429


def _make_response_with_retry_after(value: str) -> SimpleNamespace:
    return SimpleNamespace(headers={"retry-after": value})


# ---------- _parse_retry_after ----------


def test_parse_retry_after_from_lowercase_header() -> None:
    exc = _FakeRateLimitError("rate limited")
    exc.response = _make_response_with_retry_after("48")  # type: ignore[attr-defined]
    assert _parse_retry_after(exc) == 48.0


def test_parse_retry_after_from_uppercase_header() -> None:
    exc = _FakeRateLimitError("rate limited")
    exc.response = SimpleNamespace(headers={"Retry-After": "60"})  # type: ignore[attr-defined]
    assert _parse_retry_after(exc) == 60.0


def test_parse_retry_after_from_attribute() -> None:
    exc = _FakeRateLimitError("rate limited")
    exc.retry_after = 30  # type: ignore[attr-defined]
    assert _parse_retry_after(exc) == 30.0


def test_parse_retry_after_none_when_absent() -> None:
    assert _parse_retry_after(_FakeRateLimitError("boom")) is None


# ---------- _is_rate_limit_error ----------


def test_is_rate_limit_by_status_code() -> None:
    assert _is_rate_limit_error(_FakeRateLimitError("429"))


def test_is_not_rate_limit_by_status_code() -> None:
    class _Other(Exception):
        status_code = 500

    assert not _is_rate_limit_error(_Other())


# ---------- _estimate_prompt_tokens ----------


def test_estimate_prompt_tokens_fallback_on_no_litellm(monkeypatch: pytest.MonkeyPatch) -> None:
    """When litellm.token_counter isn't available, falls back to char/4."""
    # Force the helper to hit the fallback path by raising on the litellm
    # import helper.
    import flowforge_server.services.ai as ai_module

    monkeypatch.setattr(
        ai_module,
        "_get_litellm",
        lambda: SimpleNamespace(token_counter=None),
    )
    messages = [{"role": "user", "content": "x" * 400}]
    est = _estimate_prompt_tokens("claude-sonnet-4-6", messages)
    # 400 chars / 4 ≈ 100 tokens
    assert 90 <= est <= 110


# ---------- AIService.complete on 429 ----------


@pytest.mark.asyncio
async def test_complete_returns_rate_limited_on_429(monkeypatch: pytest.MonkeyPatch) -> None:
    """AIService.complete must return a structured rate-limit marker instead
    of raising when the provider returns 429."""
    service = AIService.__new__(AIService)  # skip __init__ side effects
    service._provider_registry = None
    service._health_checker = None
    service._redis = None
    service._structured_service = None

    # Cache-key path short-circuits before we get to the completion — bypass
    # by disabling cache.
    async def _no_cached(_key: str) -> None:
        return None

    service._get_cached = AsyncMock(side_effect=_no_cached)  # type: ignore[method-assign]
    service._set_cached = AsyncMock()  # type: ignore[method-assign]
    service._cache_key = MagicMock(return_value=None)  # type: ignore[method-assign]
    service._record_provider_use = MagicMock()  # type: ignore[method-assign]

    rate_limit_exc = _FakeRateLimitError("throttled")
    rate_limit_exc.response = _make_response_with_retry_after("48")  # type: ignore[attr-defined]

    mock_litellm = MagicMock()
    mock_litellm.acompletion = AsyncMock(side_effect=rate_limit_exc)
    # Expose the fake class as `RateLimitError` so _is_rate_limit_error's
    # isinstance() check hits.
    mock_litellm.RateLimitError = _FakeRateLimitError

    with patch("flowforge_server.services.ai._get_litellm", return_value=mock_litellm):
        response = await service.complete(
            model="claude-sonnet-4-6",
            messages=[{"role": "user", "content": "hi"}],
            use_cache=False,
        )

    assert isinstance(response, AIResponse)
    assert response.finish_reason == "rate_limited"
    assert response.raw_response.get("__rate_limited") is True
    assert response.raw_response.get("__retry_after") == 48.0
    assert response.raw_response.get("__provider") == "anthropic"
    assert response.raw_response.get("__model") == "claude-sonnet-4-6"
    # No inline retry: litellm should have been called exactly once.
    assert mock_litellm.acompletion.await_count == 1


@pytest.mark.asyncio
async def test_complete_other_errors_still_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-rate-limit errors must still bubble up to the executor."""
    service = AIService.__new__(AIService)
    service._provider_registry = None
    service._health_checker = None
    service._redis = None
    service._structured_service = None
    service._get_cached = AsyncMock(return_value=None)  # type: ignore[method-assign]
    service._set_cached = AsyncMock()  # type: ignore[method-assign]
    service._cache_key = MagicMock(return_value=None)  # type: ignore[method-assign]
    service._record_provider_use = MagicMock()  # type: ignore[method-assign]

    class _Timeout(Exception):
        status_code = 504

    mock_litellm = MagicMock()
    mock_litellm.acompletion = AsyncMock(side_effect=_Timeout("slow"))
    mock_litellm.RateLimitError = _FakeRateLimitError

    with patch("flowforge_server.services.ai._get_litellm", return_value=mock_litellm):
        with pytest.raises(_Timeout):
            await service.complete(
                model="claude-sonnet-4-6",
                messages=[{"role": "user", "content": "hi"}],
                use_cache=False,
            )


@pytest.mark.asyncio
async def test_complete_passes_num_retries_zero_to_litellm() -> None:
    """We must disable LiteLLM's inline retry (num_retries=0) so retries
    happen durably in the SDK, not blocking the executor worker."""
    service = AIService.__new__(AIService)
    service._provider_registry = None
    service._health_checker = None
    service._redis = None
    service._structured_service = None
    service._get_cached = AsyncMock(return_value=None)  # type: ignore[method-assign]
    service._set_cached = AsyncMock()  # type: ignore[method-assign]
    service._cache_key = MagicMock(return_value=None)  # type: ignore[method-assign]
    service._record_provider_use = MagicMock()  # type: ignore[method-assign]

    mock_response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="ok", tool_calls=None), finish_reason="stop")],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        model="claude-sonnet-4-6",
    )
    mock_litellm = MagicMock()
    mock_litellm.acompletion = AsyncMock(return_value=mock_response)
    mock_litellm.RateLimitError = _FakeRateLimitError

    with patch("flowforge_server.services.ai._get_litellm", return_value=mock_litellm):
        await service.complete(
            model="claude-sonnet-4-6",
            messages=[{"role": "user", "content": "hi"}],
            use_cache=False,
        )

    call_kwargs = mock_litellm.acompletion.await_args.kwargs
    assert call_kwargs["num_retries"] == 0
