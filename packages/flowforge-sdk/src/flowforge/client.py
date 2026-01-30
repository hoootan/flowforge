"""FlowForge client for sending events and managing functions."""

from datetime import datetime
from typing import Any, Callable, Awaitable, TypeVar
import hashlib
import hmac
import json
import os
import uuid

import httpx

from flowforge.context import Context, Event
from flowforge.triggers import TriggerBuilder
from flowforge.config import (
    Concurrency,
    RateLimit,
    Throttle,
    Debounce,
    concurrency as make_concurrency,
    rate_limit as make_rate_limit,
    throttle as make_throttle,
    debounce as make_debounce,
)
from flowforge.decorators import FlowForgeFunction, function as make_function
from flowforge.execution import ExecutionEngine, FunctionDefinition

T = TypeVar("T")


class FlowForge:
    """
    FlowForge client for building durable AI workflows.

    The client provides:
    - Function decorator for defining workflows
    - Event sending for triggering functions
    - Configuration helpers for flow control
    - Framework integrations (FastAPI, Flask, etc.)

    Example:
        from flowforge import FlowForge, Context, step

        flowforge = FlowForge(
            app_id="my-app",
            api_url="http://localhost:8000",
            api_key="ff_live_...",  # Optional: API key for authentication
        )

        @flowforge.function(
            id="process-order",
            trigger=flowforge.trigger.event("order/created"),
        )
        async def process_order(ctx: Context) -> dict:
            order = ctx.event.data
            result = await step.run("validate", validate_order, order)
            return {"status": "completed"}

        # Send an event
        await flowforge.send("order/created", data={"order_id": "123"})
    """

    def __init__(
        self,
        app_id: str,
        api_url: str | None = None,
        api_key: str | None = None,
        signing_key: str | None = None,
    ) -> None:
        """
        Initialize the FlowForge client.

        Args:
            app_id: Unique identifier for your application.
            api_url: URL of the FlowForge API server. 
                     Defaults to FLOWFORGE_API_URL env var or http://localhost:8000.
            api_key: API key for authentication (ff_live_xxx format).
                     Defaults to FLOWFORGE_API_KEY env var.
            signing_key: Key for signing webhook requests.
                         Defaults to FLOWFORGE_SIGNING_KEY env var.
        """
        self.app_id = app_id
        self.api_url = (
            api_url 
            or os.environ.get("FLOWFORGE_API_URL") 
            or os.environ.get("FLOWFORGE_SERVER_URL")  # Backward compat
            or "http://localhost:8000"
        ).rstrip("/")
        self.api_key = api_key or os.environ.get("FLOWFORGE_API_KEY")
        self.signing_key = signing_key or os.environ.get("FLOWFORGE_SIGNING_KEY")

        # Trigger builder
        self.trigger = TriggerBuilder()

        # Function registry
        self._functions: dict[str, FlowForgeFunction] = {}

        # Execution engine
        self._engine = ExecutionEngine()

        # HTTP client
        self._http_client: httpx.AsyncClient | None = None

    # Configuration helpers
    @staticmethod
    def concurrency(limit: int, key: str | None = None) -> Concurrency:
        """Create a concurrency configuration."""
        return make_concurrency(limit, key)

    @staticmethod
    def rate_limit(limit: int, period: str, key: str | None = None) -> RateLimit:
        """Create a rate limit configuration."""
        return make_rate_limit(limit, period, key)

    @staticmethod
    def throttle(
        limit: int, period: str, key: str | None = None, burst: int | None = None
    ) -> Throttle:
        """Create a throttle configuration."""
        return make_throttle(limit, period, key, burst)

    @staticmethod
    def debounce(period: str, key: str | None = None) -> Debounce:
        """Create a debounce configuration."""
        return make_debounce(period, key)

    def function(
        self,
        id: str,
        *,
        trigger: Any = None,
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

        Args:
            id: Unique identifier for this function.
            trigger: How this function is triggered.
            name: Human-readable name.
            retries: Number of retry attempts.
            timeout: Maximum execution time.
            concurrency: Concurrency configuration.
            rate_limit: Rate limiting configuration.
            throttle: Throttle configuration.
            debounce: Debounce configuration.
            cancel_on: Events that cancel running instances.
            idempotency_key: Expression for deduplication.

        Returns:
            Decorator for the function.
        """

        def decorator(fn: Callable[[Context], Awaitable[T]]) -> FlowForgeFunction:
            # Create the wrapped function
            wrapped = make_function(
                id=id,
                trigger=trigger,
                name=name,
                retries=retries,
                timeout=timeout,
                concurrency=concurrency,
                rate_limit=rate_limit,
                throttle=throttle,
                debounce=debounce,
                cancel_on=cancel_on,
                idempotency_key=idempotency_key,
            )(fn)

            # Register with the client
            self._functions[id] = wrapped

            # Register with the execution engine
            self._engine.function_registry[id] = FunctionDefinition(
                id=id,
                name=wrapped.name,
                handler=wrapped,
                trigger=trigger,
                config=wrapped.config.to_dict(),
            )

            return wrapped

        return decorator

    @property
    def functions(self) -> list[FlowForgeFunction]:
        """Get all registered functions."""
        return list(self._functions.values())

    def get_function(self, function_id: str) -> FlowForgeFunction | None:
        """Get a function by ID."""
        return self._functions.get(function_id)

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=self.api_url,
                timeout=30.0,
            )
        return self._http_client

    def _sign_request(self, body: bytes) -> str:
        """Sign a request body with the signing key."""
        if not self.signing_key:
            raise ValueError("Signing key is required for request signing")

        signature = hmac.new(
            self.signing_key.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()

        return f"sha256={signature}"

    async def send(
        self,
        name: str,
        data: dict[str, Any],
        id: str | None = None,
        timestamp: datetime | None = None,
        user_id: str | None = None,
    ) -> str:
        """
        Send an event to trigger functions.

        Args:
            name: Event type name (e.g., "order/created").
            data: Event payload data.
            id: Optional idempotency key (auto-generated if not provided).
            timestamp: Event timestamp (defaults to now).
            user_id: Optional user ID associated with the event.

        Returns:
            The event ID.

        Example:
            event_id = await flowforge.send(
                "order/created",
                data={"order_id": "123", "total": 99.99},
            )
        """
        event_id = id or str(uuid.uuid4())
        event_timestamp = timestamp or datetime.utcnow()

        event = {
            "id": event_id,
            "name": name,
            "data": data,
            "timestamp": event_timestamp.isoformat() + "Z",
            "user_id": user_id,
        }

        client = await self._get_client()

        headers = {
            "Content-Type": "application/json",
        }

        if self.api_key:
            headers["X-FlowForge-API-Key"] = self.api_key

        body = json.dumps(event).encode()

        if self.signing_key:
            headers["X-FlowForge-Signature"] = self._sign_request(body)

        response = await client.post(
            "/api/v1/events",
            content=body,
            headers=headers,
        )
        response.raise_for_status()

        return event_id

    async def send_many(self, events: list[dict[str, Any] | Event]) -> list[str]:
        """
        Send multiple events in a batch.

        Args:
            events: List of events to send.

        Returns:
            List of event IDs.

        Example:
            event_ids = await flowforge.send_many([
                {"name": "user/signup", "data": {"user_id": "1"}},
                {"name": "user/signup", "data": {"user_id": "2"}},
            ])
        """
        event_ids = []

        for event in events:
            if isinstance(event, Event):
                event_id = await self.send(
                    name=event.name,
                    data=event.data,
                    id=event.id,
                    timestamp=event.timestamp,
                    user_id=event.user_id,
                )
            else:
                event_id = await self.send(
                    name=event["name"],
                    data=event.get("data", {}),
                    id=event.get("id"),
                    timestamp=event.get("timestamp"),
                    user_id=event.get("user_id"),
                )
            event_ids.append(event_id)

        return event_ids

    def serve(
        self,
        functions: list[FlowForgeFunction] | None = None,
        host: str = "0.0.0.0",
        port: int = 8080,
    ) -> None:
        """
        Start a local development server.

        Args:
            functions: Functions to serve (uses registered functions if not provided).
            host: Host to bind to.
            port: Port to listen on.
        """
        from flowforge.dev.server import run_dev_server

        fns = functions or list(self._functions.values())
        run_dev_server(self, fns, host=host, port=port)

    def work(
        self,
        functions: list[FlowForgeFunction] | None = None,
        server_url: str | None = None,
        host: str = "0.0.0.0",
        port: int = 8080,
        worker_url: str | None = None,
    ) -> None:
        """
        Start as a worker connected to the central FlowForge server.

        This mode:
        1. Registers functions with the central server
        2. Exposes an /invoke endpoint for the server to call
        3. Handles function execution

        Args:
            functions: Functions to serve (uses registered functions if not provided).
            server_url: URL of the central FlowForge server.
            host: Host to bind to.
            port: Port to listen on.
            worker_url: URL where this worker can be reached by the server.
        """
        from flowforge.worker import run_worker

        fns = functions or list(self._functions.values())
        run_worker(
            self,
            fns,
            server_url=server_url,
            host=host,
            port=port,
            worker_url=worker_url,
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    async def __aenter__(self) -> "FlowForge":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
