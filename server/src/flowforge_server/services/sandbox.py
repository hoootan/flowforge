"""Sandboxed code execution for custom tools.

This module provides secure execution of user-defined Python code
using RestrictedPython with carefully controlled builtins and
timeout enforcement.
"""

import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

from RestrictedPython import compile_restricted, safe_builtins
from RestrictedPython.Eval import default_guarded_getiter, default_guarded_getitem
from RestrictedPython.Guards import (
    guarded_iter_unpack_sequence,
    safer_getattr,
)


# Default timeout for tool execution (30 seconds)
DEFAULT_TIMEOUT_SECONDS = 30


class SandboxError(Exception):
    """Base exception for sandbox errors."""
    pass


class SandboxCompilationError(SandboxError):
    """Error during code compilation."""
    pass


class SandboxExecutionError(SandboxError):
    """Error during code execution."""
    pass


class SandboxTimeoutError(SandboxError):
    """Execution timed out."""
    pass


class SandboxSecurityError(SandboxError):
    """Security violation detected."""
    pass


# Whitelist of safe builtins for tool execution
SAFE_BUILTINS = {
    **safe_builtins,
    # Allow basic types
    "True": True,
    "False": False,
    "None": None,
    # Allow safe type conversions
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
    "tuple": tuple,
    "set": set,
    "frozenset": frozenset,
    # Allow iteration
    "range": range,
    "enumerate": enumerate,
    "zip": zip,
    "map": map,
    "filter": filter,
    "sorted": sorted,
    "reversed": reversed,
    # Allow basic operations
    "len": len,
    "sum": sum,
    "min": min,
    "max": max,
    "abs": abs,
    "round": round,
    "pow": pow,
    "divmod": divmod,
    # Allow string operations
    "ord": ord,
    "chr": chr,
    "repr": repr,
    "format": format,
    # Allow type checking
    "isinstance": isinstance,
    "issubclass": issubclass,
    "type": type,
    "hasattr": hasattr,
    # Allow exceptions (read-only access)
    "Exception": Exception,
    "ValueError": ValueError,
    "TypeError": TypeError,
    "KeyError": KeyError,
    "IndexError": IndexError,
    # Allow JSON (import-safe)
    "json": __import__("json"),
    # Allow datetime for common use cases
    "datetime": __import__("datetime"),
    # Allow math module
    "math": __import__("math"),
    # Allow re for pattern matching
    "re": __import__("re"),
}

# Modules that are explicitly blocked
BLOCKED_MODULES = {
    "os", "sys", "subprocess", "shutil", "socket", "signal",
    "ctypes", "multiprocessing", "threading", "asyncio",
    "pickle", "marshal", "builtins", "importlib", "code",
    "codeop", "compileall", "dis", "inspect", "pdb",
    "trace", "traceback", "linecache", "gc", "atexit",
    "io", "pathlib", "tempfile", "glob", "fnmatch",
    "requests", "urllib", "http", "httpx", "aiohttp",
    "sqlite3", "psycopg2", "pymongo", "redis", "sqlalchemy",
}


def _guarded_import(
    name: str,
    globals_dict: dict | None = None,
    locals_dict: dict | None = None,
    fromlist: tuple = (),
    level: int = 0,
) -> Any:
    """Restricted import function that only allows safe modules."""
    if name in BLOCKED_MODULES:
        raise SandboxSecurityError(f"Import of module '{name}' is not allowed")

    # Only allow json, datetime, math, re
    allowed_imports = {"json", "datetime", "math", "re", "collections", "itertools", "functools"}
    if name not in allowed_imports:
        raise SandboxSecurityError(f"Import of module '{name}' is not allowed")

    return __import__(name, globals_dict, locals_dict, fromlist, level)


def _write_guard(obj: Any) -> Any:
    """Guard for write operations - restricts what can be modified."""
    # Only allow writing to dicts and lists created within the sandbox
    if isinstance(obj, (dict, list)):
        return obj
    raise SandboxSecurityError(f"Cannot modify objects of type {type(obj).__name__}")


def _create_restricted_globals() -> dict[str, Any]:
    """Create the restricted globals for sandboxed execution."""
    return {
        "__builtins__": SAFE_BUILTINS,
        "__name__": "__sandbox__",
        "__doc__": None,
        # RestrictedPython guards
        "_getattr_": safer_getattr,
        "_getitem_": default_guarded_getitem,
        "_getiter_": default_guarded_getiter,
        "_iter_unpack_sequence_": guarded_iter_unpack_sequence,
        "_write_": _write_guard,
        "_print_": lambda *args, **kwargs: None,  # Disable print
        "__import__": _guarded_import,
    }


def compile_sandboxed(code: str, filename: str = "<sandbox>") -> Any:
    """
    Compile Python code using RestrictedPython.

    Args:
        code: Python source code to compile
        filename: Filename for error messages

    Returns:
        Compiled code object

    Raises:
        SandboxCompilationError: If compilation fails
    """
    result = compile_restricted(code, filename, "exec")

    if result.errors:
        error_msgs = "\n".join(result.errors)
        raise SandboxCompilationError(f"Compilation failed:\n{error_msgs}")

    return result.code


def execute_sandboxed_sync(
    code: str,
    arguments: dict[str, Any],
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> Any:
    """
    Execute sandboxed code synchronously.

    Args:
        code: Python source code defining an 'execute' function
        arguments: Arguments to pass to the execute function
        timeout_seconds: Maximum execution time

    Returns:
        Result from the execute function

    Raises:
        SandboxError: If execution fails
    """
    # Compile the code
    compiled = compile_sandboxed(code)

    # Create restricted globals
    globals_dict = _create_restricted_globals()

    # Execute the code to define functions
    exec(compiled, globals_dict)

    # Get the execute function
    execute_fn = globals_dict.get("execute")
    if execute_fn is None:
        raise SandboxExecutionError("Tool code must define an 'execute' function")

    if not callable(execute_fn):
        raise SandboxExecutionError("'execute' must be a callable function")

    # Execute with timeout
    def run_with_result() -> Any:
        return execute_fn(**arguments)

    # Use a thread pool to run with timeout
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(run_with_result)
        try:
            return future.result(timeout=timeout_seconds)
        except TimeoutError:
            raise SandboxTimeoutError(
                f"Tool execution timed out after {timeout_seconds} seconds"
            )
        except Exception as e:
            raise SandboxExecutionError(f"Tool execution failed: {str(e)}")


async def execute_sandboxed(
    code: str,
    arguments: dict[str, Any],
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> Any:
    """
    Execute sandboxed code asynchronously.

    This runs the synchronous execution in a thread pool to avoid
    blocking the event loop.

    Args:
        code: Python source code defining an 'execute' function
        arguments: Arguments to pass to the execute function
        timeout_seconds: Maximum execution time

    Returns:
        Result from the execute function

    Raises:
        SandboxError: If execution fails
    """
    loop = asyncio.get_event_loop()

    # Run the synchronous execution in a thread pool
    result = await asyncio.wait_for(
        loop.run_in_executor(
            None,
            functools.partial(
                execute_sandboxed_sync,
                code,
                arguments,
                timeout_seconds,
            ),
        ),
        timeout=timeout_seconds + 1,  # Extra second for thread overhead
    )

    return result


async def execute_async_sandboxed(
    code: str,
    arguments: dict[str, Any],
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> Any:
    """
    Execute sandboxed code that may define an async execute function.

    This supports both sync and async execute functions.

    Args:
        code: Python source code defining an 'execute' function
        arguments: Arguments to pass to the execute function
        timeout_seconds: Maximum execution time

    Returns:
        Result from the execute function

    Raises:
        SandboxError: If execution fails
    """
    # For async functions, we can't use RestrictedPython's compile_restricted
    # because it doesn't support async/await syntax well.
    # Instead, we'll run sync code in a sandboxed environment.
    #
    # If async support is needed, the tool should be a built-in or
    # use a webhook-based execution model.

    return await execute_sandboxed(code, arguments, timeout_seconds)


def validate_tool_code(code: str) -> list[str]:
    """
    Validate tool code without executing it.

    Args:
        code: Python source code to validate

    Returns:
        List of validation errors (empty if valid)
    """
    errors: list[str] = []

    # Check for obvious security issues in source
    dangerous_patterns = [
        ("__import__", "Direct __import__ calls are not allowed"),
        ("exec(", "exec() calls are not allowed"),
        ("eval(", "eval() calls are not allowed"),
        ("compile(", "compile() calls are not allowed"),
        ("open(", "File operations are not allowed"),
        ("globals(", "globals() access is not allowed"),
        ("locals(", "locals() access is not allowed"),
        ("__builtins__", "__builtins__ access is not allowed"),
        ("__code__", "__code__ access is not allowed"),
        ("__class__", "__class__ access is not allowed"),
        ("__bases__", "__bases__ access is not allowed"),
        ("__subclasses__", "__subclasses__ access is not allowed"),
        ("os.", "os module access is not allowed"),
        ("sys.", "sys module access is not allowed"),
        ("subprocess", "subprocess module is not allowed"),
    ]

    for pattern, message in dangerous_patterns:
        if pattern in code:
            errors.append(message)

    # Try to compile
    try:
        compile_sandboxed(code)
    except SandboxCompilationError as e:
        errors.append(str(e))

    # Check for execute function
    if "def execute" not in code:
        errors.append("Tool code must define an 'execute' function")

    return errors
