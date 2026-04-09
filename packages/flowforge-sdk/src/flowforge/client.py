"""FlowForge client for sending events and managing functions."""

import hashlib
import hmac
import json
import os
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import datetime
from typing import Any, TypeVar

import httpx

from flowforge.config import (
    Concurrency,
    Debounce,
    RateLimit,
    Throttle,
)
from flowforge.config import (
    concurrency as make_concurrency,
)
from flowforge.config import (
    debounce as make_debounce,
)
from flowforge.config import (
    rate_limit as make_rate_limit,
)
from flowforge.config import (
    throttle as make_throttle,
)
from flowforge.context import Context, Event
from flowforge.decorators import FlowForgeFunction
from flowforge.decorators import function as make_function
from flowforge.execution import ExecutionEngine, FunctionDefinition
from flowforge.streaming import RunEvent, RunEventType
from flowforge.triggers import TriggerBuilder

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

    async def get_run(self, run_id: str) -> dict[str, Any]:
        """
        Get details for a specific run.

        Args:
            run_id: The run UUID.

        Returns:
            Run details including status, steps, and output.
        """
        client = await self._get_client()
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-FlowForge-API-Key"] = self.api_key
        response = await client.get(f"/api/v1/runs/{run_id}", headers=headers)
        response.raise_for_status()
        return response.json()

    async def cancel_run(self, run_id: str) -> dict[str, Any]:
        """
        Cancel a running or pending run.

        Args:
            run_id: The run UUID to cancel.

        Returns:
            Action result with success status.
        """
        client = await self._get_client()
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-FlowForge-API-Key"] = self.api_key
        response = await client.post(f"/api/v1/runs/{run_id}/cancel", headers=headers)
        response.raise_for_status()
        return response.json()

    async def retry_run(self, run_id: str) -> dict[str, Any]:
        """
        Retry a failed run in-place, preserving all completed (memoized) steps.

        Unlike replay (which starts a fresh run), retry keeps all memoized step
        results so execution resumes from the point of failure rather than from
        the beginning.

        Args:
            run_id: The run UUID to retry.

        Returns:
            Action result with success status.

        Example:
            result = await flowforge.retry_run("761c0321-...")
            print(result["message"])  # "Run queued for retry..."
        """
        client = await self._get_client()
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-FlowForge-API-Key"] = self.api_key
        response = await client.post(f"/api/v1/runs/{run_id}/retry", headers=headers)
        response.raise_for_status()
        return response.json()

    async def stream_run(
        self,
        run_id: str,
        *,
        include_history: bool = True,
        timeout: float = 300.0,
        on_event: Callable[[RunEvent], None] | None = None,
    ) -> AsyncIterator[RunEvent]:
        """
        Stream real-time SSE events for a run.

        Args:
            run_id: The run UUID to stream.
            include_history: Whether to include past events on connect.
            timeout: Server-side stream timeout in seconds.
            on_event: Optional callback invoked for each event.

        Yields:
            RunEvent for each SSE event. Stops on terminal events
            (run_completed, run_failed).

        Example:
            async for event in flowforge.stream_run("run-uuid"):
                print(f"[{event.event_type.value}] {event.data}")
        """
        params = {
            "include_history": str(include_history).lower(),
            "timeout": str(int(timeout)),
        }
        url = f"{self.api_url}/api/v1/runs/{run_id}/stream"

        headers: dict[str, str] = {"Accept": "text/event-stream"}
        if self.api_key:
            headers["X-FlowForge-API-Key"] = self.api_key

        # Use a dedicated client with extended read timeout for streaming
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=timeout + 30.0, write=10.0, pool=10.0),
        ) as client:
            async with client.stream(
                "GET", url, params=params, headers=headers,
            ) as response:
                response.raise_for_status()

                event_type: str | None = None
                data_buf: list[str] = []

                async for line in response.aiter_lines():
                    # Skip keepalive comments
                    if line.startswith(":"):
                        continue

                    # Blank line = dispatch event
                    if not line:
                        if event_type and data_buf:
                            raw_data = "\n".join(data_buf)
                            try:
                                evt = RunEvent.from_raw(event_type, raw_data, run_id)
                            except (ValueError, json.JSONDecodeError):
                                event_type = None
                                data_buf = []
                                continue

                            if on_event:
                                on_event(evt)
                            yield evt

                            if evt.is_terminal:
                                return

                        event_type = None
                        data_buf = []
                        continue

                    if line.startswith("event:"):
                        event_type = line[len("event:"):].strip()
                    elif line.startswith("data:"):
                        data_buf.append(line[len("data:"):].strip())

    # ── Agent Management ──────────────────────────────────────────

    async def list_agents(self) -> list[dict[str, Any]]:
        """List all agents for the current tenant."""
        client = await self._get_client()
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-FlowForge-API-Key"] = self.api_key
        response = await client.get("/api/v1/agents", headers=headers)
        response.raise_for_status()
        return response.json().get("agents", [])

    async def create_agent(
        self,
        name: str,
        *,
        description: str | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
        capabilities: dict[str, Any] | None = None,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create a new agent.

        Args:
            name: Display name for the agent.
            description: What the agent does.
            model: Default AI model (e.g., "claude-sonnet-4-6").
            system_prompt: Agent personality/instructions.
            capabilities: Agent capabilities dict.
            config: Agent configuration dict.

        Returns:
            Created agent details.
        """
        client = await self._get_client()
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-FlowForge-API-Key"] = self.api_key
        payload: dict[str, Any] = {"name": name}
        if description:
            payload["description"] = description
        if model:
            payload["model"] = model
        if system_prompt:
            payload["system_prompt"] = system_prompt
        if capabilities:
            payload["capabilities"] = capabilities
        if config:
            payload["config"] = config
        response = await client.post("/api/v1/agents", json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

    async def update_agent(
        self,
        agent_id: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Update an agent's properties."""
        client = await self._get_client()
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-FlowForge-API-Key"] = self.api_key
        response = await client.patch(
            f"/api/v1/agents/{agent_id}",
            json=kwargs,
            headers=headers,
        )
        response.raise_for_status()
        return response.json()

    # ── Task Management ───────────────────────────────────────────

    async def list_tasks(
        self,
        *,
        status: str | None = None,
        assignee_agent_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """List tasks with optional filters."""
        client = await self._get_client()
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-FlowForge-API-Key"] = self.api_key
        params: dict[str, str] = {}
        if status:
            params["status"] = status
        if assignee_agent_id:
            params["assignee_agent_id"] = assignee_agent_id
        response = await client.get("/api/v1/tasks", params=params, headers=headers)
        response.raise_for_status()
        return response.json().get("tasks", [])

    async def create_task(
        self,
        title: str,
        *,
        description: str | None = None,
        priority: str = "none",
        assignee_agent_id: str | None = None,
        assignee_user_id: str | None = None,
        function_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new task.

        Args:
            title: Task title.
            description: Task description (markdown).
            priority: One of "urgent", "high", "medium", "low", "none".
            assignee_agent_id: Assign to an agent.
            assignee_user_id: Assign to a user.
            function_id: Link to a FlowForge function.

        Returns:
            Created task with identifier (e.g., FF-1).
        """
        client = await self._get_client()
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-FlowForge-API-Key"] = self.api_key
        payload: dict[str, Any] = {"title": title, "priority": priority}
        if description:
            payload["description"] = description
        if assignee_agent_id:
            payload["assignee_agent_id"] = assignee_agent_id
        if assignee_user_id:
            payload["assignee_user_id"] = assignee_user_id
        if function_id:
            payload["function_id"] = function_id
        response = await client.post("/api/v1/tasks", json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

    async def update_task(
        self,
        task_id: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Update a task (status, assignment, etc.)."""
        client = await self._get_client()
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-FlowForge-API-Key"] = self.api_key
        response = await client.patch(
            f"/api/v1/tasks/{task_id}",
            json=kwargs,
            headers=headers,
        )
        response.raise_for_status()
        return response.json()

    # ── Comments / Collaboration ──────────────────────────────────

    async def add_comment(
        self,
        *,
        task_id: str | None = None,
        run_id: str | None = None,
        content: str,
        author_agent_id: str | None = None,
        author_user_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Add a comment to a task or run.

        Args:
            task_id: Comment on a task.
            run_id: Comment on a run.
            content: Comment text (markdown).
            author_agent_id: Agent author.
            author_user_id: User author.

        Returns:
            Created comment details.
        """
        client = await self._get_client()
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-FlowForge-API-Key"] = self.api_key
        payload: dict[str, Any] = {"content": content}
        if task_id:
            payload["task_id"] = task_id
        if run_id:
            payload["run_id"] = run_id
        if author_agent_id:
            payload["author_agent_id"] = author_agent_id
        if author_user_id:
            payload["author_user_id"] = author_user_id
        response = await client.post("/api/v1/comments", json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

    # ── Skills ────────────────────────────────────────────────────

    async def list_skills(
        self,
        *,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        """List available skill templates."""
        client = await self._get_client()
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-FlowForge-API-Key"] = self.api_key
        params: dict[str, str] = {}
        if category:
            params["category"] = category
        response = await client.get("/api/v1/skills", params=params, headers=headers)
        response.raise_for_status()
        return response.json().get("skills", [])

    async def create_skill(
        self,
        name: str,
        *,
        description: str | None = None,
        category: str | None = None,
        function_config: dict[str, Any] | None = None,
        tools_config: list[dict[str, Any]] | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Save a function+tools configuration as a reusable skill template."""
        client = await self._get_client()
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-FlowForge-API-Key"] = self.api_key
        payload: dict[str, Any] = {"name": name}
        if description:
            payload["description"] = description
        if category:
            payload["category"] = category
        if function_config:
            payload["function_config"] = function_config
        if tools_config:
            payload["tools_config"] = tools_config
        if tags:
            payload["tags"] = tags
        response = await client.post("/api/v1/skills", json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

    async def search_marketplace(
        self,
        query: str,
        *,
        source: str = "skills_sh",
        limit: int = 10,
    ) -> dict[str, Any]:
        """Search the skills.sh marketplace for community-built agent skills."""
        client = await self._get_client()
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-FlowForge-API-Key"] = self.api_key
        params = {"q": query, "source": source, "limit": str(limit)}
        response = await client.get("/api/v1/skills/marketplace/search", params=params, headers=headers)
        response.raise_for_status()
        return response.json()

    async def preview_marketplace_skill(
        self,
        repo: str,
        path: str = "SKILL.md",
    ) -> dict[str, Any]:
        """Preview a SKILL.md from a GitHub repository before importing."""
        client = await self._get_client()
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-FlowForge-API-Key"] = self.api_key
        params = {"repo": repo, "path": path}
        response = await client.get("/api/v1/skills/marketplace/preview", params=params, headers=headers)
        response.raise_for_status()
        return response.json()

    async def import_marketplace_skill(
        self,
        repo: str,
        *,
        path: str = "SKILL.md",
        source: str = "skills_sh",
        name: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Import a skill from the marketplace into FlowForge."""
        client = await self._get_client()
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-FlowForge-API-Key"] = self.api_key
        payload: dict[str, Any] = {"repo": repo, "path": path, "source": source}
        if name:
            payload["name_override"] = name
        if category:
            payload["category"] = category
        if tags:
            payload["tags"] = tags
        response = await client.post("/api/v1/skills/marketplace/import", json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    async def __aenter__(self) -> "FlowForge":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
