"""Unit tests for the sandbox module."""

import pytest

from flowforge_server.services.sandbox import (
    SandboxCompilationError,
    SandboxExecutionError,
    SandboxSecurityError,
    SandboxTimeoutError,
    compile_sandboxed,
    execute_sandboxed,
    execute_sandboxed_sync,
    validate_tool_code,
)


class TestCompileSandboxed:
    """Tests for compile_sandboxed function."""

    def test_compile_valid_code(self):
        """Test compiling valid Python code."""
        code = """
def execute(x: int) -> int:
    return x * 2
"""
        result = compile_sandboxed(code)
        assert result is not None

    def test_compile_syntax_error(self):
        """Test compiling code with syntax errors."""
        code = """
def execute(x: int)
    return x * 2
"""
        with pytest.raises(SandboxCompilationError):
            compile_sandboxed(code)

    def test_compile_restricted_attribute_access(self):
        """Test that restricted attribute access is blocked."""
        code = """
def execute() -> str:
    return "".__class__.__bases__[0].__subclasses__()
"""
        with pytest.raises(SandboxCompilationError):
            compile_sandboxed(code)


class TestExecuteSandboxedSync:
    """Tests for execute_sandboxed_sync function."""

    def test_execute_simple_function(self):
        """Test executing a simple function."""
        code = """
def execute(x: int, y: int) -> int:
    return x + y
"""
        result = execute_sandboxed_sync(code, {"x": 5, "y": 3})
        assert result == 8

    def test_execute_with_string_operations(self):
        """Test executing with string operations."""
        code = """
def execute(text: str) -> str:
    return text.upper()
"""
        result = execute_sandboxed_sync(code, {"text": "hello"})
        assert result == "HELLO"

    def test_execute_with_list_operations(self):
        """Test executing with list operations."""
        code = """
def execute(items: list) -> list:
    return sorted(items)
"""
        result = execute_sandboxed_sync(code, {"items": [3, 1, 2]})
        assert result == [1, 2, 3]

    def test_execute_with_dict_operations(self):
        """Test executing with dict operations."""
        code = """
def execute(data: dict) -> dict:
    result = {}
    for k, v in data.items():
        result[k.upper()] = v * 2
    return result
"""
        result = execute_sandboxed_sync(code, {"data": {"a": 1, "b": 2}})
        assert result == {"A": 2, "B": 4}

    def test_execute_with_json(self):
        """Test executing with json module."""
        code = """
import json

def execute(data: dict) -> str:
    return json.dumps(data)
"""
        result = execute_sandboxed_sync(code, {"data": {"key": "value"}})
        assert result == '{"key": "value"}'

    def test_execute_with_math(self):
        """Test executing with math module."""
        code = """
import math

def execute(x: float) -> float:
    return math.sqrt(x)
"""
        result = execute_sandboxed_sync(code, {"x": 16.0})
        assert result == 4.0

    def test_execute_missing_execute_function(self):
        """Test error when execute function is missing."""
        code = """
def other_function(x: int) -> int:
    return x * 2
"""
        with pytest.raises(SandboxExecutionError, match="must define an 'execute' function"):
            execute_sandboxed_sync(code, {})

    def test_execute_blocked_import(self):
        """Test that dangerous imports are blocked."""
        code = """
import os

def execute() -> str:
    return os.getcwd()
"""
        with pytest.raises(SandboxSecurityError, match="not allowed"):
            execute_sandboxed_sync(code, {})

    def test_execute_blocked_subprocess(self):
        """Test that subprocess is blocked."""
        code = """
import subprocess

def execute() -> str:
    return subprocess.run(["ls"], capture_output=True).stdout
"""
        with pytest.raises(SandboxSecurityError, match="not allowed"):
            execute_sandboxed_sync(code, {})

    def test_execute_timeout(self):
        """Test that infinite loops are terminated."""
        code = """
def execute() -> int:
    i = 0
    while True:
        i += 1
    return i
"""
        with pytest.raises(SandboxTimeoutError):
            execute_sandboxed_sync(code, {}, timeout_seconds=1)


class TestValidateToolCode:
    """Tests for validate_tool_code function."""

    def test_validate_valid_code(self):
        """Test validating valid tool code."""
        code = """
def execute(query: str) -> dict:
    return {"result": query.upper()}
"""
        errors = validate_tool_code(code)
        assert len(errors) == 0

    def test_validate_missing_execute(self):
        """Test validation catches missing execute function."""
        code = """
def other_function(x: int) -> int:
    return x * 2
"""
        errors = validate_tool_code(code)
        assert any("execute" in e for e in errors)

    def test_validate_dangerous_pattern_exec(self):
        """Test validation catches exec() calls."""
        code = """
def execute(code: str) -> None:
    exec(code)
"""
        errors = validate_tool_code(code)
        assert any("exec()" in e for e in errors)

    def test_validate_dangerous_pattern_eval(self):
        """Test validation catches eval() calls."""
        code = """
def execute(expr: str) -> any:
    return eval(expr)
"""
        errors = validate_tool_code(code)
        assert any("eval()" in e for e in errors)

    def test_validate_dangerous_pattern_open(self):
        """Test validation catches open() calls."""
        code = """
def execute(path: str) -> str:
    with open(path) as f:
        return f.read()
"""
        errors = validate_tool_code(code)
        assert any("File operations" in e for e in errors)

    def test_validate_dangerous_pattern_os(self):
        """Test validation catches os module access."""
        code = """
import os

def execute() -> str:
    return os.getcwd()
"""
        errors = validate_tool_code(code)
        assert any("os module" in e for e in errors)


@pytest.mark.asyncio
class TestExecuteSandboxedAsync:
    """Tests for async execute_sandboxed function."""

    async def test_async_execute_simple(self):
        """Test async execution of simple function."""
        code = """
def execute(x: int) -> int:
    return x * 2
"""
        result = await execute_sandboxed(code, {"x": 5})
        assert result == 10

    async def test_async_execute_timeout(self):
        """Test async timeout handling."""
        code = """
def execute() -> int:
    i = 0
    while True:
        i += 1
    return i
"""
        with pytest.raises(SandboxTimeoutError):
            await execute_sandboxed(code, {}, timeout_seconds=1)


class TestSandboxCredentials:
    """Tests for the ``credentials`` global injected into the sandbox."""

    def test_credentials_get_returns_value(self):
        code = """
def execute() -> str:
    return credentials.get("api_key")
"""
        result = execute_sandboxed_sync(
            code, {}, credentials={"api_key": "secret-123"}
        )
        assert result == "secret-123"

    def test_credentials_get_missing_returns_default(self):
        code = """
def execute() -> str:
    return credentials.get("missing", "fallback")
"""
        result = execute_sandboxed_sync(code, {}, credentials={"other": "x"})
        assert result == "fallback"

    def test_credentials_get_missing_returns_none(self):
        code = """
def execute():
    return credentials.get("missing")
"""
        result = execute_sandboxed_sync(code, {}, credentials={})
        assert result is None

    def test_credentials_default_empty_when_omitted(self):
        code = """
def execute():
    return credentials.get("api_key")
"""
        # No credentials kwarg → empty dict → returns None.
        result = execute_sandboxed_sync(code, {})
        assert result is None

    def test_credentials_in_operator(self):
        code = """
def execute() -> bool:
    return "api_key" in credentials
"""
        result = execute_sandboxed_sync(code, {}, credentials={"api_key": "v"})
        assert result is True

    def test_credentials_cannot_enumerate(self):
        # No iter / keys / values — tools can't probe for cred names.
        code = """
def execute():
    return list(credentials)
"""
        with pytest.raises(SandboxExecutionError):
            execute_sandboxed_sync(code, {}, credentials={"a": "1", "b": "2"})

    def test_credentials_no_keys_method(self):
        code = """
def execute():
    return credentials.keys()
"""
        with pytest.raises(SandboxExecutionError):
            execute_sandboxed_sync(code, {}, credentials={"a": "1"})

    def test_credentials_no_subscript_access(self):
        # Only .get() is allowed; bracket access is not exposed.
        code = """
def execute():
    return credentials["api_key"]
"""
        with pytest.raises(SandboxExecutionError):
            execute_sandboxed_sync(code, {}, credentials={"api_key": "v"})

    async def test_credentials_passed_through_async_entrypoint(self):
        code = """
def execute() -> str:
    return credentials.get("token")
"""
        result = await execute_sandboxed(
            code, {}, credentials={"token": "async-tok"}
        )
        assert result == "async-tok"

    def test_existing_tools_unaffected_when_credentials_omitted(self):
        # Regression: prior call sites that don't pass credentials still work.
        code = """
def execute(x: int, y: int) -> int:
    return x + y
"""
        assert execute_sandboxed_sync(code, {"x": 2, "y": 3}) == 5
