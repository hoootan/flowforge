"""Decorators for defining FlowForge functions."""

from functools import wraps
from typing import Any, Callable, TypeVar, Awaitable, ParamSpec
import asyncio
import inspect

from flowforge.context import Context
from flowforge.triggers import Trigger
from flowforge.config import Concurrency, RateLimit, Throttle, Debounce, FunctionConfig

P = ParamSpec("P")
T = TypeVar("T")


class FlowForgeFunction:
    """
    Wrapper for a FlowForge function with its configuration.

    This class wraps user-defined functions and stores their
    configuration for registration with the FlowForge client.
    """

    def __init__(
        self,
        handler: Callable[[Context], Awaitable[Any]],
        id: str,
        name: str | None = None,
        trigger: Trigger | None = None,
        retries: int = 3,
        timeout: str = "5m",
        concurrency: Concurrency | None = None,
        rate_limit: RateLimit | None = None,
        throttle: Throttle | None = None,
        debounce: Debounce | None = None,
        cancel_on: list[str] | None = None,
        idempotency_key: str | None = None,
    ) -> None:
        self._handler = handler
        self.id = id
        self.name = name or handler.__name__
        self.trigger = trigger
        self.config = FunctionConfig(
            id=id,
            name=self.name,
            retries=retries,
            timeout=timeout,
            concurrency=concurrency,
            rate_limit=rate_limit,
            throttle=throttle,
            debounce=debounce,
            cancel_on=cancel_on or [],
            idempotency_key=idempotency_key,
        )

        # Preserve function metadata
        self.__name__ = handler.__name__
        self.__doc__ = handler.__doc__
        self.__module__ = handler.__module__

    async def __call__(self, ctx: Context) -> Any:
        """Execute the wrapped function."""
        return await self._handler(ctx)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for registration."""
        result = self.config.to_dict()
        if self.trigger:
            result["trigger"] = self.trigger.to_dict()
        return result


def function(
    id: str,
    *,
    trigger: Trigger | None = None,
    name: str | None = None,
    retries: int = 3,
    timeout: str = "5m",
    concurrency: Concurrency | None = None,
    rate_limit: RateLimit | None = None,
    throttle: Throttle | None = None,
    debounce: Debounce | None = None,
    cancel_on: list[str] | None = None,
    idempotency_key: str | None = None,
) -> Callable[[Callable[[Context], Awaitable[T]]], FlowForgeFunction]:
    """
    Decorator to define a FlowForge function.

    This decorator wraps an async function and registers it as a
    FlowForge workflow function with the specified configuration.

    Args:
        id: Unique identifier for this function (e.g., "process-order").
        trigger: How this function is triggered (event, cron, webhook).
        name: Human-readable name (defaults to function name).
        retries: Number of retry attempts on failure (default: 3).
        timeout: Maximum execution time (default: "5m").
        concurrency: Concurrency limiting configuration.
        rate_limit: Rate limiting configuration.
        throttle: Throttle configuration.
        debounce: Debounce configuration.
        cancel_on: List of events that cancel running instances.
        idempotency_key: Expression for deduplication.

    Returns:
        A decorator that wraps the function.

    Example:
        from flowforge import FlowForge, Context, step

        flowforge = FlowForge(app_id="my-app")

        @flowforge.function(
            id="process-order",
            trigger=flowforge.trigger.event("order/created"),
            retries=3,
            timeout="10m",
            concurrency=flowforge.concurrency(limit=10),
        )
        async def process_order(ctx: Context) -> dict:
            order = ctx.event.data

            # Steps are automatically retried and memoized
            validated = await step.run("validate", validate_order, order)
            payment = await step.run("charge", charge_payment, order["total"])

            return {"status": "completed"}
    """

    def decorator(fn: Callable[[Context], Awaitable[T]]) -> FlowForgeFunction:
        # Ensure the function is async
        if not asyncio.iscoroutinefunction(fn):
            raise TypeError(
                f"FlowForge functions must be async. "
                f"Add 'async' to the function definition: async def {fn.__name__}(...)"
            )

        # Validate function signature
        sig = inspect.signature(fn)
        params = list(sig.parameters.values())

        if len(params) != 1:
            raise TypeError(
                f"FlowForge functions must accept exactly one parameter (ctx: Context). "
                f"Got {len(params)} parameters in {fn.__name__}."
            )

        # Wrap the function
        wrapped = FlowForgeFunction(
            handler=fn,
            id=id,
            name=name,
            trigger=trigger,
            retries=retries,
            timeout=timeout,
            concurrency=concurrency,
            rate_limit=rate_limit,
            throttle=throttle,
            debounce=debounce,
            cancel_on=cancel_on,
            idempotency_key=idempotency_key,
        )

        return wrapped

    return decorator
