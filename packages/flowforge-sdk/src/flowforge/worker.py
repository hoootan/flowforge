"""Worker mode for FlowForge - connects to central server."""

from typing import Any, TYPE_CHECKING
import asyncio
import os

if TYPE_CHECKING:
    from flowforge.client import FlowForge
    from flowforge.decorators import FlowForgeFunction


async def _register_functions(
    server_url: str,
    app_id: str,
    functions: list["FlowForgeFunction"],
    worker_url: str,
) -> None:
    """Register functions with the central FlowForge server."""
    import httpx

    async with httpx.AsyncClient(timeout=30.0) as client:
        for fn in functions:
            # Build function registration payload
            trigger_data = {
                "type": fn.trigger.type if fn.trigger else "event",
                "value": fn.trigger.value if fn.trigger else "",
                "expression": fn.trigger.expression if fn.trigger else None,
            }

            payload = {
                "id": fn.id,
                "name": fn.name or fn.id,
                "trigger": trigger_data,
                "endpoint_url": worker_url,
                "config": {
                    "retries": fn.config.retries,
                    "timeout": fn.config.timeout,
                },
            }

            try:
                response = await client.post(
                    f"{server_url}/api/v1/functions",
                    json=payload,
                )
                response.raise_for_status()
                print(f"[Worker] Registered function: {fn.id}")
            except httpx.HTTPStatusError as e:
                print(f"[Worker] Failed to register {fn.id}: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                print(f"[Worker] Failed to register {fn.id}: {e}")


def run_worker(
    flowforge: "FlowForge",
    functions: list["FlowForgeFunction"],
    server_url: str | None = None,
    host: str = "0.0.0.0",
    port: int = 8080,
    worker_url: str | None = None,
) -> None:
    """
    Start the FlowForge worker.

    The worker:
    1. Registers functions with the central server
    2. Exposes an /invoke endpoint for the server to call
    3. Handles function execution

    Args:
        flowforge: The FlowForge client instance.
        functions: List of functions to serve.
        server_url: URL of the central FlowForge server.
        host: Host to bind to.
        port: Port to listen on.
        worker_url: URL where this worker can be reached by the server.
    """
    try:
        import uvicorn
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse
    except ImportError:
        raise ImportError(
            "FastAPI and uvicorn are required for the worker. "
            "Install with: pip install flowforge-sdk[fastapi]"
        )

    # Get server URL from env or parameter
    server_url = server_url or os.environ.get("FLOWFORGE_SERVER_URL", "http://localhost:8000")

    # Worker URL - how the server can reach us
    worker_url = worker_url or os.environ.get(
        "FLOWFORGE_WORKER_URL",
        f"http://localhost:{port}/api/flowforge"
    )

    app = FastAPI(
        title="FlowForge Worker",
        description="Worker process for FlowForge functions",
    )

    # Mount the FlowForge invoke endpoint
    from flowforge.integrations.fastapi import serve
    serve(app, flowforge, functions, path="/api/flowforge")

    @app.get("/")
    async def root() -> dict[str, Any]:
        return {
            "name": "FlowForge Worker",
            "app_id": flowforge.app_id,
            "server_url": server_url,
            "functions": [fn.id for fn in functions],
        }

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "healthy",
            "app_id": flowforge.app_id,
            "functions": len(functions),
        }

    @app.on_event("startup")
    async def on_startup() -> None:
        """Register functions with the server on startup."""
        print(f"[Worker] Registering {len(functions)} functions with {server_url}...")
        await _register_functions(server_url, flowforge.app_id, functions, worker_url)
        print(f"[Worker] Registration complete")

    print(f"\n{'='*60}")
    print(f"  FlowForge Worker")
    print(f"{'='*60}")
    print(f"  App ID:      {flowforge.app_id}")
    print(f"  Server URL:  {server_url}")
    print(f"  Worker URL:  {worker_url}")
    print(f"  Functions:   {len(functions)}")
    for fn in functions:
        trigger_info = ""
        if fn.trigger:
            trigger_info = f" (trigger: {fn.trigger.type}={fn.trigger.value})"
        print(f"    - {fn.id}{trigger_info}")
    print(f"{'='*60}\n")

    uvicorn.run(app, host=host, port=port, log_level="info")
