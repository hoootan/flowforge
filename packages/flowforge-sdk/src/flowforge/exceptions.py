"""FlowForge exceptions for workflow control flow and error handling."""

from typing import Any


class FlowForgeError(Exception):
    """Base exception for all FlowForge errors."""

    pass


class StepError(FlowForgeError):
    """Base exception for step-related errors."""

    def __init__(self, step_id: str, message: str) -> None:
        self.step_id = step_id
        super().__init__(f"Step '{step_id}': {message}")


class StepCompleted(FlowForgeError):
    """
    Raised when a step completes successfully.

    This is a control flow exception used by the execution engine to yield
    control back to the server after each step. The server will save the
    result and re-invoke the function to continue execution.
    """

    def __init__(self, step_id: str, result: Any, started_at: str | None = None) -> None:
        self.step_id = step_id
        self.result = result
        self.started_at = started_at  # ISO 8601 timestamp
        super().__init__(f"Step '{step_id}' completed")


class StepFailed(StepError):
    """Raised when a step fails after all retries are exhausted."""

    def __init__(
        self,
        step_id: str,
        error: Exception | str,
        attempt: int = 1,
        max_attempts: int = 1,
    ) -> None:
        self.original_error = error
        self.attempt = attempt
        self.max_attempts = max_attempts
        message = f"failed after {attempt}/{max_attempts} attempts: {error}"
        super().__init__(step_id, message)


class StepTimeout(StepError):
    """Raised when a step exceeds its timeout."""

    def __init__(self, step_id: str, timeout_seconds: float) -> None:
        self.timeout_seconds = timeout_seconds
        super().__init__(step_id, f"timed out after {timeout_seconds}s")


class RetryableError(StepFailed):
    """
    Raised to indicate an error that should trigger a retry.

    Used for transient failures (rate limits, brief network issues). Subclasses
    StepFailed so existing `except StepFailed` catchers still catch it; callers
    that want retry-specific behaviour can catch RetryableError directly.
    """

    def __init__(
        self,
        message: str = "",
        *,
        step_id: str = "",
        retry_after: float | None = None,
        attempt: int = 1,
        max_attempts: int = 1,
    ) -> None:
        self.retry_after = retry_after
        super().__init__(step_id, message, attempt=attempt, max_attempts=max_attempts)


class RateLimited(RetryableError):
    """
    Raised when an LLM provider rate-limited the request and retries exhausted.

    Carries enough context for callers to decide follow-up behaviour (switch
    providers, surface to the user, park the run).

    Aliases:
      - ``self.original`` / ``self.original_error`` — both point at the
        underlying provider exception (or its string form). Error payloads
        serialised via ``str(e.original_error)`` therefore surface the real
        root cause, not the synthesised "rate limited by …" banner.
    """

    def __init__(
        self,
        *,
        step_id: str = "",
        retry_after: float | None = None,
        provider: str = "",
        model: str = "",
        original: Exception | str = "",
        attempt: int = 1,
        max_attempts: int = 1,
    ) -> None:
        self.provider = provider
        self.model = model
        self.original = original
        # Pass `original` through StepFailed so `e.original_error` reflects
        # the underlying provider failure. The exception's __str__ still
        # includes a readable banner via the StepError base message.
        banner = f"rate limited by {provider or 'provider'} on {model or 'model'}"
        super().__init__(
            original if original else banner,
            step_id=step_id,
            retry_after=retry_after,
            attempt=attempt,
            max_attempts=max_attempts,
        )


class NonRetryableError(FlowForgeError):
    """
    Raised to indicate an error that should NOT be retried.

    Use this to immediately fail a step without retrying,
    e.g., for validation errors or permanent failures.
    """

    pass


class FunctionNotFoundError(FlowForgeError):
    """Raised when a function cannot be found."""

    def __init__(self, function_id: str) -> None:
        self.function_id = function_id
        super().__init__(f"Function '{function_id}' not found")


class EventValidationError(FlowForgeError):
    """Raised when an event fails validation."""

    pass


class ConfigurationError(FlowForgeError):
    """Raised when there's a configuration error."""

    pass


class AuthenticationError(FlowForgeError):
    """Raised when authentication fails."""

    pass


class WaitForEventTimeout(StepError):
    """Raised when wait_for_event times out."""

    def __init__(self, step_id: str, event_name: str, timeout: str) -> None:
        self.event_name = event_name
        self.timeout = timeout
        super().__init__(step_id, f"timed out waiting for event '{event_name}' after {timeout}")
