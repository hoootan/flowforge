"""Unit tests for tenant-credential pre-resolution into the sandbox.

Covers the wiring between ``InlineExecutor._resolve_tenant_credentials`` and
``InlineExecutor._execute_custom_tool``: the executor must (1) load only the
calling tenant's *active* credentials, (2) decrypt each one, (3) hand the
plaintext dict to the sandbox, and (4) survive a single bad row without
failing the whole tool invocation.

These are unit tests — the DB session is a stub and ``decrypt_value`` is
monkey-patched, so the suite does not require Postgres.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from flowforge_server.services import inline_executor as inline_executor_module
from flowforge_server.services.inline_executor import InlineExecutor


class _FakeCredentialRow:
    def __init__(self, name: str, encrypted_value: str, value_prefix: str = "xxx") -> None:
        self.name = name
        self.encrypted_value = encrypted_value
        self.value_prefix = value_prefix


class _FakeScalarsResult:
    def __init__(self, rows: list[_FakeCredentialRow]) -> None:
        self._rows = rows

    def all(self) -> list[_FakeCredentialRow]:
        return self._rows


class _FakeExecuteResult:
    def __init__(self, rows: list[_FakeCredentialRow]) -> None:
        self._rows = rows

    def scalars(self) -> _FakeScalarsResult:
        return _FakeScalarsResult(self._rows)


class _FakeSession:
    """Stub AsyncSession that returns a canned set of Credential rows.

    Tracks the most recent ``select`` statement so tests can assert that
    the query filters by ``tenant_id`` and ``is_active``.
    """

    def __init__(self, rows: list[_FakeCredentialRow]) -> None:
        self._rows = rows
        self.last_stmt: Any = None

    async def execute(self, stmt: Any) -> _FakeExecuteResult:
        self.last_stmt = stmt
        return _FakeExecuteResult(self._rows)


@pytest.fixture
def stub_decrypt(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Replace decrypt_value with a deterministic mapping for the test."""
    mapping = {
        "enc-tavily": "tavily-plaintext",
        "enc-apify": "apify-plaintext",
        "enc-broken": "should-not-be-reached",
    }

    def fake_decrypt(ciphertext: str) -> str:
        if ciphertext == "enc-broken":
            raise ValueError("simulated decryption failure")
        return mapping[ciphertext]

    monkeypatch.setattr(inline_executor_module, "decrypt_value", fake_decrypt)
    return mapping


class TestResolveTenantCredentials:
    async def test_returns_decrypted_active_credentials(self, stub_decrypt):
        tenant_id = uuid.uuid4()
        session = _FakeSession([
            _FakeCredentialRow("tavily_api_key", "enc-tavily"),
            _FakeCredentialRow("apify_api_key", "enc-apify"),
        ])
        executor = InlineExecutor(ai_service=None)  # type: ignore[arg-type]

        resolved = await executor._resolve_tenant_credentials(session, tenant_id)

        assert resolved == {
            "tavily_api_key": "tavily-plaintext",
            "apify_api_key": "apify-plaintext",
        }

    async def test_query_filters_by_tenant_and_active(self, stub_decrypt):
        tenant_id = uuid.uuid4()
        session = _FakeSession([])
        executor = InlineExecutor(ai_service=None)  # type: ignore[arg-type]

        await executor._resolve_tenant_credentials(session, tenant_id)

        # The compiled SELECT should mention both filters; we don't run it
        # against a real DB but we can sanity-check the WHERE clause text.
        rendered = str(
            session.last_stmt.compile(compile_kwargs={"literal_binds": True})
        )
        assert "tenant_id" in rendered
        assert "is_active" in rendered

    async def test_empty_when_tenant_has_no_credentials(self, stub_decrypt):
        executor = InlineExecutor(ai_service=None)  # type: ignore[arg-type]
        session = _FakeSession([])
        resolved = await executor._resolve_tenant_credentials(session, uuid.uuid4())
        assert resolved == {}

    async def test_one_bad_credential_does_not_fail_others(self, stub_decrypt):
        executor = InlineExecutor(ai_service=None)  # type: ignore[arg-type]
        session = _FakeSession([
            _FakeCredentialRow("good", "enc-tavily"),
            _FakeCredentialRow("broken", "enc-broken"),
            _FakeCredentialRow("good2", "enc-apify"),
        ])
        resolved = await executor._resolve_tenant_credentials(session, uuid.uuid4())
        assert resolved == {"good": "tavily-plaintext", "good2": "apify-plaintext"}
        assert "broken" not in resolved


class TestCustomToolReceivesCredentials:
    """End-to-end through ``_execute_custom_tool`` without a real DB."""

    async def test_tool_can_read_credentials_via_get(self, stub_decrypt):
        executor = InlineExecutor(ai_service=None)  # type: ignore[arg-type]
        session = _FakeSession([
            _FakeCredentialRow("tavily_api_key", "enc-tavily"),
        ])
        code = """
def execute() -> str:
    return credentials.get("tavily_api_key")
"""
        result = await executor._execute_custom_tool(
            code, {}, session=session, tenant_id=uuid.uuid4()
        )
        assert result == "tavily-plaintext"

    async def test_tool_gets_none_for_missing_credential(self, stub_decrypt):
        executor = InlineExecutor(ai_service=None)  # type: ignore[arg-type]
        session = _FakeSession([])
        code = """
def execute():
    return credentials.get("not_set")
"""
        result = await executor._execute_custom_tool(
            code, {}, session=session, tenant_id=uuid.uuid4()
        )
        assert result is None

    async def test_no_session_means_empty_credentials(self, stub_decrypt):
        # Backwards-compat path: callers that don't pass session/tenant_id
        # still work; the tool just sees an empty credentials view.
        executor = InlineExecutor(ai_service=None)  # type: ignore[arg-type]
        code = """
def execute() -> bool:
    return "any" in credentials
"""
        result = await executor._execute_custom_tool(code, {})
        assert result is False
