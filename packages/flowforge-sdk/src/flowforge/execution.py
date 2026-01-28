"""Execution engine for FlowForge functions."""

from typing import Any, Callable, Awaitable
import json
import traceback

from flowforge.context import Context, Event
from flowforge.exceptions import (
    StepCompleted,
    StepFailed,
    FlowForgeError,
    NonRetryableError,
)
from flowforge.steps import StepManager, step as global_step, _hash_step_id


class ExecutionResult:
    """Result of a function execution."""

    def __init__(
        self,
        status: str,
        step_id: str | None = None,
        step_result: Any = None,
        output: Any = None,
        error: dict[str, Any] | None = None,
    ) -> None:
        self.status = status  # "step_complete", "function_complete", "error"
        self.step_id = step_id
        self.step_result = step_result
        self.output = output
        self.error = error

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"status": self.status}

        if self.step_id:
            result["step_id"] = self.step_id
            result["step_hash"] = _hash_step_id(self.step_id)

        if self.step_result is not None:
            result["step_result"] = self.step_result

        if self.output is not None:
            result["output"] = self.output

        if self.error:
            result["error"] = self.error

        return result


class ExecutionEngine:
    """
    Executes FlowForge functions with step memoization.

    The execution engine is responsible for:
    - Creating the execution context
    - Setting up step memoization
    - Catching step completion exceptions
    - Returning results to the server
    """

    def __init__(self, function_registry: dict[str, "FunctionDefinition"] | None = None) -> None:
        self.function_registry = function_registry or {}

    async def execute(
        self,
        function_id: str,
        event: Event,
        run_id: str,
        completed_steps: dict[str, Any],
        attempt: int = 1,
    ) -> ExecutionResult:
        """
        Execute a function with the given context.

        Args:
            function_id: The ID of the function to execute.
            event: The triggering event.
            run_id: The run ID for this execution.
            completed_steps: Dictionary of already-completed step results.
            attempt: Current attempt number.

        Returns:
            ExecutionResult indicating the execution outcome.
        """
        # Get the function
        fn_def = self.function_registry.get(function_id)
        if fn_def is None:
            return ExecutionResult(
                status="error",
                error={
                    "type": "FunctionNotFound",
                    "message": f"Function '{function_id}' not found",
                    "retryable": False,
                },
            )

        # Create step manager with completed steps
        step_manager = StepManager(run_id=run_id, completed_steps=completed_steps)

        # Create context
        ctx = Context(
            event=event,
            run_id=run_id,
            function_id=function_id,
            attempt=attempt,
            _step_manager=step_manager,
        )

        # Set global step manager for module-level step access
        global_step._current_manager = step_manager

        try:
            # Execute the function
            result = await fn_def.handler(ctx)

            # Function completed successfully
            return ExecutionResult(
                status="function_complete",
                output=result,
            )

        except StepCompleted as e:
            # Step completed, yield to server
            return ExecutionResult(
                status="step_complete",
                step_id=e.step_id,
                step_result=e.result,
            )

        except StepFailed as e:
            # Step failed, let server handle retry
            return ExecutionResult(
                status="error",
                step_id=e.step_id,
                error={
                    "type": "StepFailed",
                    "message": str(e.original_error),
                    "step_id": e.step_id,
                    "attempt": e.attempt,
                    "max_attempts": e.max_attempts,
                    "retryable": True,
                    "traceback": traceback.format_exc(),
                },
            )

        except NonRetryableError as e:
            # Non-retryable error, fail immediately
            return ExecutionResult(
                status="error",
                error={
                    "type": "NonRetryableError",
                    "message": str(e),
                    "retryable": False,
                    "traceback": traceback.format_exc(),
                },
            )

        except Exception as e:
            # Unexpected error, may be retryable
            return ExecutionResult(
                status="error",
                error={
                    "type": type(e).__name__,
                    "message": str(e),
                    "retryable": True,
                    "traceback": traceback.format_exc(),
                },
            )

        finally:
            # Clear global step manager
            global_step._current_manager = None


class FunctionDefinition:
    """Definition of a registered FlowForge function."""

    def __init__(
        self,
        id: str,
        name: str,
        handler: Callable[[Context], Awaitable[Any]],
        trigger: Any,
        config: dict[str, Any],
    ) -> None:
        self.id = id
        self.name = name
        self.handler = handler
        self.trigger = trigger
        self.config = config

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "trigger": self.trigger.to_dict() if hasattr(self.trigger, "to_dict") else self.trigger,
            "config": self.config,
        }
