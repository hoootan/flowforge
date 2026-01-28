"""FastAPI integration for FlowForge SDK."""

from typing import Any, TYPE_CHECKING
import hashlib
import hmac
import json

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse

if TYPE_CHECKING:
    from flowforge.client import FlowForge
    from flowforge.decorators import FlowForgeFunction


async def _handle_invoke(
    request: Request,
    flowforge: "FlowForge",
    functions: list["FlowForgeFunction"],
) -> Response:
    """Handle function invocation from the FlowForge server."""
    from flowforge.context import Event
    from flowforge.execution import ExecutionEngine, FunctionDefinition

    # Parse request body
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # Validate required fields
    function_id = body.get("function_id")
    if not function_id:
        raise HTTPException(status_code=400, detail="Missing function_id")

    # Find the function
    fn = None
    for f in functions:
        if f.id == function_id:
            fn = f
            break

    if fn is None:
        fn = flowforge.get_function(function_id)

    if fn is None:
        return JSONResponse(
            status_code=404,
            content={
                "status": "error",
                "error": {
                    "type": "FunctionNotFound",
                    "message": f"Function '{function_id}' not found",
                    "retryable": False,
                },
            },
        )

    # Build event
    event_data = body.get("event", {})
    event = Event(
        id=event_data.get("id", ""),
        name=event_data.get("name", ""),
        data=event_data.get("data", {}),
        timestamp=event_data.get("timestamp", ""),
        user_id=event_data.get("user_id"),
    )

    # Get run context
    run_id = body.get("run_id", "")
    completed_steps = body.get("steps", {})
    attempt = body.get("attempt", 1)

    # Create execution engine with this function
    engine = ExecutionEngine()
    engine.function_registry[function_id] = FunctionDefinition(
        id=fn.id,
        name=fn.name,
        handler=fn,
        trigger=fn.trigger,
        config=fn.config.to_dict(),
    )

    # Execute
    result = await engine.execute(
        function_id=function_id,
        event=event,
        run_id=run_id,
        completed_steps=completed_steps,
        attempt=attempt,
    )

    return JSONResponse(content=result.to_dict())


async def _handle_register(
    request: Request,
    flowforge: "FlowForge",
    functions: list["FlowForgeFunction"],
) -> Response:
    """Handle function registration request."""
    function_defs = []

    for fn in functions:
        fn_def = fn.to_dict()
        function_defs.append(fn_def)

    # Also include functions registered directly on the client
    for fn in flowforge.functions:
        if fn not in functions:
            fn_def = fn.to_dict()
            function_defs.append(fn_def)

    return JSONResponse(
        content={
            "app_id": flowforge.app_id,
            "functions": function_defs,
        }
    )


def serve(
    app: FastAPI,
    flowforge: "FlowForge",
    functions: list["FlowForgeFunction"] | None = None,
    path: str = "/api/flowforge",
) -> None:
    """
    Mount FlowForge endpoints on a FastAPI application.

    This creates endpoints for:
    - POST {path}/invoke - Function invocation from the server
    - GET {path}/register - Function registration/discovery

    Args:
        app: The FastAPI application to mount on.
        flowforge: The FlowForge client instance.
        functions: List of functions to serve (uses registered if not provided).
        path: Base path for FlowForge endpoints.

    Example:
        from fastapi import FastAPI
        from flowforge import FlowForge
        from flowforge.integrations.fastapi import serve

        app = FastAPI()
        flowforge = FlowForge(app_id="my-app")

        @flowforge.function(id="my-func", trigger=flowforge.trigger.event("test"))
        async def my_func(ctx):
            return {"result": "ok"}

        serve(app, flowforge, path="/api/flowforge")
    """
    fns = functions or list(flowforge._functions.values())

    @app.post(f"{path}/invoke")
    async def invoke_handler(request: Request) -> Response:
        return await _handle_invoke(request, flowforge, fns)

    @app.get(f"{path}/register")
    async def register_handler(request: Request) -> Response:
        return await _handle_register(request, flowforge, fns)

    @app.get(f"{path}/health")
    async def health_handler() -> dict[str, Any]:
        return {
            "status": "healthy",
            "app_id": flowforge.app_id,
            "functions": len(fns),
        }
