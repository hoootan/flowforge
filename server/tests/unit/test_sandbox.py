"""Unit tests for the sandbox module."""

import pytest
from flowforge_server.services.sandbox import (
    compile_sandboxed,
    execute_sandboxed_sync,
    execute_sandboxed,
    validate_tool_code,
    SandboxCompilationError,
    SandboxExecutionError,
    SandboxSecurityError,
    SandboxTimeoutError,
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
