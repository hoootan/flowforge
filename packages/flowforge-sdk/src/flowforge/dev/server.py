"""Local development server for FlowForge functions."""

from typing import Any, TYPE_CHECKING
import asyncio
import json
import uuid
from datetime import datetime

if TYPE_CHECKING:
    from flowforge.client import FlowForge
    from flowforge.decorators import FlowForgeFunction


class LocalDevServer:
    """
    Local development server for testing FlowForge functions.

    This server provides:
    - Function invocation endpoint
    - Event simulation
    - Step execution with memoization
    - Local state storage (in-memory)
    """

    def __init__(
        self,
        flowforge: "FlowForge",
        functions: list["FlowForgeFunction"],
    ) -> None:
        self.flowforge = flowforge
        self.functions = {fn.id: fn for fn in functions}

        # In-memory storage for local dev
        self.events: list[dict[str, Any]] = []
        self.runs: dict[str, dict[str, Any]] = {}
        self.steps: dict[str, dict[str, Any]] = {}

    def get_function(self, function_id: str) -> "FlowForgeFunction | None":
        """Get a function by ID."""
        return self.functions.get(function_id)

    async def send_event(
        self,
        name: str,
        data: dict[str, Any],
        id: str | None = None,
    ) -> str:
        """Send an event and trigger matching functions."""
        from flowforge.context import Event
        from flowforge.execution import ExecutionEngine, FunctionDefinition

        event_id = id or str(uuid.uuid4())
        now = datetime.utcnow()

        # Store event
        event_record = {
            "id": event_id,
            "name": name,
            "data": data,
            "timestamp": now.isoformat(),
            "received_at": now.isoformat(),
        }
        self.events.append(event_record)

        print(f"[FlowForge] Event received: {name} ({event_id})")

        # Find matching functions
        matching = []
        for fn in self.functions.values():
            if fn.trigger and fn.trigger.type == "event" and fn.trigger.value == name:
                matching.append(fn)

        # Execute matching functions
        for fn in matching:
            run_id = str(uuid.uuid4())
            print(f"[FlowForge] Starting run: {fn.id} ({run_id[:8]}...)")

            # Create run record
            self.runs[run_id] = {
                "id": run_id,
                "function_id": fn.id,
                "event_id": event_id,
                "status": "running",
                "started_at": now.isoformat(),
                "completed_steps": {},
            }

            # Execute function
            await self._execute_run(run_id, fn, event_record)

        return event_id

    async def _execute_run(
        self,
        run_id: str,
        fn: "FlowForgeFunction",
        event_data: dict[str, Any],
    ) -> None:
        """Execute a function run with step-by-step processing."""
        from flowforge.context import Event
        from flowforge.execution import ExecutionEngine, FunctionDefinition

        run = self.runs[run_id]
        max_iterations = 100  # Safety limit

        for iteration in range(max_iterations):
            # Build event
            event = Event(
                id=event_data["id"],
                name=event_data["name"],
                data=event_data["data"],
                timestamp=event_data["timestamp"],
            )

            # Create execution engine
            engine = ExecutionEngine()
            engine.function_registry[fn.id] = FunctionDefinition(
                id=fn.id,
                name=fn.name,
                handler=fn,
                trigger=fn.trigger,
                config=fn.config.to_dict(),
            )

            # Execute with current completed steps
            result = await engine.execute(
                function_id=fn.id,
                event=event,
                run_id=run_id,
                completed_steps=run["completed_steps"],
                attempt=1,
            )

            if result.status == "step_complete":
                # Store step result
                step_id = result.step_id
                step_result = result.step_result

                # Check if this is a special step type
                if isinstance(step_result, dict) and "type" in step_result:
                    step_type = step_result["type"]

                    if step_type == "sleep":
                        duration = step_result.get("duration_seconds", 0)
                        print(f"[FlowForge] Step '{step_id}': sleep({duration}s) - skipping in dev mode")
                        # In dev mode, we skip sleeps
                        run["completed_steps"][result.to_dict()["step_hash"]] = None

                    elif step_type == "ai":
                        print(f"[FlowForge] Step '{step_id}': AI call to {step_result.get('model')}")
                        # Simulate AI response in dev mode
                        run["completed_steps"][result.to_dict()["step_hash"]] = {
                            "content": "[DEV MODE] Simulated AI response",
                            "model": step_result.get("model"),
                            "usage": {"prompt_tokens": 0, "completion_tokens": 0},
                        }

                    elif step_type == "wait_for_event":
                        event_name = step_result.get("event")
                        print(f"[FlowForge] Step '{step_id}': waiting for event '{event_name}' - skipping in dev mode")
                        run["completed_steps"][result.to_dict()["step_hash"]] = None

                    elif step_type == "send_event":
                        event_name = step_result.get("name")
                        event_data_inner = step_result.get("data", {})
                        print(f"[FlowForge] Step '{step_id}': sending event '{event_name}'")
                        sent_id = await self.send_event(event_name, event_data_inner)
                        run["completed_steps"][result.to_dict()["step_hash"]] = sent_id

                    else:
                        # Unknown step type, store result as-is
                        run["completed_steps"][result.to_dict()["step_hash"]] = step_result
                else:
                    # Regular step, store result
                    print(f"[FlowForge] Step '{step_id}': completed")
                    run["completed_steps"][result.to_dict()["step_hash"]] = step_result

                # Continue execution
                continue

            elif result.status == "function_complete":
                run["status"] = "completed"
                run["output"] = result.output
                run["ended_at"] = datetime.utcnow().isoformat()
                print(f"[FlowForge] Run completed: {fn.id} ({run_id[:8]}...)")
                print(f"[FlowForge] Output: {json.dumps(result.output, indent=2)}")
                return

            elif result.status == "error":
                run["status"] = "failed"
                run["error"] = result.error
                run["ended_at"] = datetime.utcnow().isoformat()
                print(f"[FlowForge] Run failed: {fn.id} ({run_id[:8]}...)")
                print(f"[FlowForge] Error: {result.error}")
                return

        # Safety limit reached
        print(f"[FlowForge] Run aborted: too many iterations ({max_iterations})")
        run["status"] = "failed"
        run["error"] = {"message": "Maximum iterations exceeded"}


def run_dev_server(
    flowforge: "FlowForge",
    functions: list["FlowForgeFunction"],
    host: str = "0.0.0.0",
    port: int = 8080,
) -> None:
    """
    Start the local development server.

    Args:
        flowforge: The FlowForge client instance.
        functions: List of functions to serve.
        host: Host to bind to.
        port: Port to listen on.
    """
    try:
        import uvicorn
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse
    except ImportError:
        raise ImportError(
            "FastAPI and uvicorn are required for the dev server. "
            "Install with: pip install flowforge-sdk[fastapi]"
        )

    app = FastAPI(
        title="FlowForge Dev Server",
        description="Local development server for FlowForge functions",
    )

    server = LocalDevServer(flowforge, functions)

    @app.get("/")
    async def root() -> dict[str, Any]:
        return {
            "name": "FlowForge Dev Server",
            "app_id": flowforge.app_id,
            "functions": list(server.functions.keys()),
        }

    @app.post("/api/v1/events")
    async def receive_event(request: Request) -> JSONResponse:
        body = await request.json()
        event_id = await server.send_event(
            name=body["name"],
            data=body.get("data", {}),
            id=body.get("id"),
        )
        return JSONResponse(
            status_code=201,
            content={"id": event_id, "status": "received"},
        )

    @app.get("/api/v1/runs")
    async def list_runs() -> dict[str, Any]:
        return {"runs": list(server.runs.values())}

    @app.get("/api/v1/runs/{run_id}")
    async def get_run(run_id: str) -> dict[str, Any]:
        if run_id not in server.runs:
            return JSONResponse(status_code=404, content={"error": "Run not found"})
        return server.runs[run_id]

    @app.get("/api/v1/events")
    async def list_events() -> dict[str, Any]:
        return {"events": server.events}

    @app.get("/api/v1/functions")
    async def list_functions() -> dict[str, Any]:
        return {
            "functions": [
                {
                    "id": fn.id,
                    "name": fn.name,
                    "trigger": fn.trigger.to_dict() if fn.trigger else None,
                }
                for fn in server.functions.values()
            ]
        }

    # Mount the FlowForge invoke endpoint
    from flowforge.integrations.fastapi import serve
    serve(app, flowforge, functions, path="/api/flowforge")

    print(f"\n{'='*60}")
    print(f"  FlowForge Dev Server")
    print(f"{'='*60}")
    print(f"  App ID:     {flowforge.app_id}")
    print(f"  Functions:  {len(functions)}")
    for fn in functions:
        trigger_info = ""
        if fn.trigger:
            trigger_info = f" (trigger: {fn.trigger.type}={fn.trigger.value})"
        print(f"    - {fn.id}{trigger_info}")
    print(f"\n  Endpoints:")
    print(f"    POST http://{host}:{port}/api/v1/events    - Send events")
    print(f"    GET  http://{host}:{port}/api/v1/runs      - List runs")
    print(f"    GET  http://{host}:{port}/api/v1/functions - List functions")
    print(f"{'='*60}\n")

    uvicorn.run(app, host=host, port=port, log_level="info")
