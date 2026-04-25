"""Sandboxed code execution for custom tools.

This module provides secure execution of user-defined Python code
using RestrictedPython with carefully controlled builtins and
timeout enforcement.
"""

import asyncio
import functools
import operator
import threading
from typing import Any

from RestrictedPython import compile_restricted, safe_builtins
from RestrictedPython.Eval import default_guarded_getitem, default_guarded_getiter
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


def _safe_http_request(url, method="GET", headers=None, json=None, timeout=30):
    """SSRF-safe HTTP request available to sandboxed tool code."""
    from flowforge_server.services.network_utils import (
        create_ssrf_safe_sync_client,
        validate_webhook_url,
    )
    validate_webhook_url(url)
    timeout = max(1, min(timeout, 60))
    with create_ssrf_safe_sync_client(timeout=timeout) as client:
        response = client.request(method, url, headers=headers or {}, json=json)
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "text": response.text,
        }


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
    # Allow SSRF-safe HTTP requests
    "http_request": _safe_http_request,
}


# Use operator.i* so mutable types (list/set/etc.) hit their __iadd__ and mutate
# in place — matches Python's real += semantics. Immutables fall back to __add__.
_INPLACE_OPS = {
    "+=": operator.iadd,
    "-=": operator.isub,
    "*=": operator.imul,
    "/=": operator.itruediv,
    "//=": operator.ifloordiv,
    "%=": operator.imod,
    "**=": operator.ipow,
    "<<=": operator.ilshift,
    ">>=": operator.irshift,
    "&=": operator.iand,
    "|=": operator.ior,
    "^=": operator.ixor,
}


def _inplace_var(op: str, x: Any, y: Any) -> Any:
    """Shim for RestrictedPython's augmented-assignment rewrite (e.g. 'n += 1')."""
    fn = _INPLACE_OPS.get(op)
    if fn is None:
        raise SandboxSecurityError(f"Unsupported inplace operator: {op}")
    return fn(x, y)

# Modules that are explicitly blocked
BLOCKED_MODULES = {
    "os", "sys", "subprocess", "shutil", "socket", "signal",
    "ctypes", "multiprocessing", "threading", "asyncio",
    "pickle", "marshal", "builtins", "importlib", "code",
    "codeop", "compileall", "dis", "inspect", "pdb",
    "trace", "traceback", "linecache", "gc", "atexit",
    "io", "pathlib", "tempfile", "glob", "fnmatch",
    "requests", "urllib", "http", "aiohttp", "httpx",
    "sqlite3", "psycopg2", "pymongo", "redis", "sqlalchemy",
}


class _ReadOnlyEnviron:
    """Read-only proxy for os.environ, safe for sandbox use."""

    def get(self, key: str, default: str | None = None) -> str | None:
        import os
        return os.environ.get(key, default)

    def __getitem__(self, key: str) -> str:
        import os
        return os.environ[key]

    def __contains__(self, key: object) -> bool:
        import os
        return key in os.environ


_SAFE_ENVIRON = _ReadOnlyEnviron()


class _SandboxCredentials:
    """Read-only view over pre-resolved credentials for the calling tenant.

    Exposed to sandboxed tool code as the ``credentials`` global. Only
    ``.get(name, default=None)`` and ``in`` are supported — no enumeration,
    no iteration, and no dict access via ``[]`` — so a tool can't probe
    for credential names it shouldn't know about.
    """

    __slots__ = ("_d",)

    def __init__(self, resolved: dict[str, str] | None = None) -> None:
        self._d = resolved or {}

    def get(self, name: str, default: str | None = None) -> str | None:
        return self._d.get(name, default)

    def __contains__(self, name: object) -> bool:
        return name in self._d


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

    # Allow json, datetime, math, re for sandbox use
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


def _create_restricted_globals(
    credentials: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Create the restricted globals for sandboxed execution.

    Args:
        credentials: Pre-resolved {name: plaintext} for the calling tenant.
            Exposed to tool code as the ``credentials`` global with a
            minimal ``.get(name, default)`` API.
    """

    # Build a safe os-like namespace with only environ access
    class _SafeOs:
        environ = _SAFE_ENVIRON

    # __import__ must live inside __builtins__ — Python's import machinery
    # looks it up there, not in module globals. RestrictedPython 8.x surfaces
    # this: putting the hook in globals alone raises ImportError at runtime.
    builtins_with_import = {**SAFE_BUILTINS, "__import__": _guarded_import}

    return {
        "__builtins__": builtins_with_import,
        "__name__": "__sandbox__",
        "__doc__": None,
        # RestrictedPython guards
        "_getattr_": safer_getattr,
        "_getitem_": default_guarded_getitem,
        "_getiter_": default_guarded_getiter,
        "_iter_unpack_sequence_": guarded_iter_unpack_sequence,
        "_inplacevar_": _inplace_var,
        "_write_": _write_guard,
        "_print_": lambda *args, **kwargs: None,  # Disable print
        # Safe os proxy for reading environment variables
        "os": _SafeOs(),
        # Tenant-scoped, pre-resolved credentials (read-only, no enumeration)
        "credentials": _SandboxCredentials(credentials),
    }


def compile_sandboxed(code: str, filename: str = "<sandbox>") -> Any:
    """
    Compile Python code using RestrictedPython.

    Handles RestrictedPython 7.x (returns CompileResult with .errors/.code)
    and 8.x (returns a raw code object; raises SyntaxError on bad syntax).
    """
    try:
        result = compile_restricted(code, filename, "exec")
    except SyntaxError as e:
        raise SandboxCompilationError(f"Compilation failed: {e}") from e

    if hasattr(result, "errors"):
        if result.errors:
            error_msgs = "\n".join(result.errors)
            raise SandboxCompilationError(f"Compilation failed:\n{error_msgs}")
        return result.code

    return result


def execute_sandboxed_sync(
    code: str,
    arguments: dict[str, Any],
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    credentials: dict[str, str] | None = None,
) -> Any:
    """
    Execute sandboxed code synchronously.

    Args:
        code: Python source code defining an 'execute' function
        arguments: Arguments to pass to the execute function
        timeout_seconds: Maximum execution time
        credentials: Optional pre-resolved {name: plaintext} dict exposed
            to tool code as the ``credentials`` global.

    Returns:
        Result from the execute function

    Raises:
        SandboxError: If execution fails
    """
    # Compile the code
    compiled = compile_sandboxed(code)

    # Create restricted globals
    globals_dict = _create_restricted_globals(credentials)

    # Execute the code to define functions
    exec(compiled, globals_dict)

    # Get the execute function
    execute_fn = globals_dict.get("execute")
    if execute_fn is None:
        raise SandboxExecutionError("Tool code must define an 'execute' function")

    if not callable(execute_fn):
        raise SandboxExecutionError("'execute' must be a callable function")

    # Run on a daemon thread so a runaway tool (infinite loop) doesn't block
    # process exit — Python cannot kill threads, but daemons die with the
    # process. A leaked daemon here is a pre-existing design limitation;
    # the hard guarantee is only the timeout surfaces to the caller.
    result_holder: dict[str, Any] = {}

    def run_with_result() -> None:
        try:
            result_holder["value"] = execute_fn(**arguments)
        except BaseException as exc:  # noqa: BLE001 — capture anything the tool raises
            result_holder["error"] = exc

    worker = threading.Thread(
        target=run_with_result, name="ff-sandbox", daemon=True
    )
    worker.start()
    worker.join(timeout=timeout_seconds)

    if worker.is_alive():
        raise SandboxTimeoutError(
            f"Tool execution timed out after {timeout_seconds} seconds"
        )

    if "error" in result_holder:
        err = result_holder["error"]
        if isinstance(err, SandboxError):
            raise err
        # `from err` chains __cause__ so the original traceback survives the
        # thread boundary in logs, while the caller still sees SandboxExecutionError.
        raise SandboxExecutionError(f"Tool execution failed: {err}") from err

    return result_holder.get("value")


async def execute_sandboxed(
    code: str,
    arguments: dict[str, Any],
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    credentials: dict[str, str] | None = None,
) -> Any:
    """
    Execute sandboxed code asynchronously.

    This runs the synchronous execution in a thread pool to avoid
    blocking the event loop.

    Args:
        code: Python source code defining an 'execute' function
        arguments: Arguments to pass to the execute function
        timeout_seconds: Maximum execution time
        credentials: Optional pre-resolved {name: plaintext} dict exposed
            to tool code as the ``credentials`` global.

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
                credentials,
            ),
        ),
        timeout=timeout_seconds + 1,  # Extra second for thread overhead
    )

    return result


async def execute_async_sandboxed(
    code: str,
    arguments: dict[str, Any],
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    credentials: dict[str, str] | None = None,
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

    return await execute_sandboxed(code, arguments, timeout_seconds, credentials)


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
