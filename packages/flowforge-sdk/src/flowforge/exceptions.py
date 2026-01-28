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

    def __init__(self, step_id: str, result: Any) -> None:
        self.step_id = step_id
        self.result = result
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


class RetryableError(FlowForgeError):
    """
    Raised to indicate an error that should trigger a retry.

    Use this to signal that the current step should be retried,
    e.g., for transient network errors or rate limits.
    """

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        self.retry_after = retry_after
        super().__init__(message)


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
