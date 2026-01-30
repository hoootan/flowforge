"""Worker mode for FlowForge - connects to central server."""

from typing import Any, TYPE_CHECKING
import asyncio
import os

if TYPE_CHECKING:
    from flowforge.client import FlowForge
    from flowforge.decorators import FlowForgeFunction

# Heartbeat interval in seconds
HEARTBEAT_INTERVAL = 30


async def _heartbeat_loop(
    server_url: str,
    function_ids: list[str],
    api_key: str | None = None,
) -> None:
    """Send periodic heartbeats to the server."""
    import httpx

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-FlowForge-API-Key"] = api_key

    while True:
        try:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{server_url}/api/v1/functions/heartbeat",
                    json=function_ids,
                    headers=headers,
                )
                if response.status_code == 200:
                    print(f"[Worker] Heartbeat sent ({len(function_ids)} functions)")
                else:
                    print(f"[Worker] Heartbeat failed: {response.status_code}")
        except asyncio.CancelledError:
            print("[Worker] Heartbeat loop cancelled")
            break
        except Exception as e:
            print(f"[Worker] Heartbeat error: {e}")


async def _register_functions(
    server_url: str,
    app_id: str,
    functions: list["FlowForgeFunction"],
    worker_url: str,
    api_key: str | None = None,
) -> None:
    """Register functions with the central FlowForge server."""
    import httpx

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-FlowForge-API-Key"] = api_key

    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
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

    # Background task for heartbeat
    heartbeat_task: asyncio.Task | None = None

    @app.on_event("startup")
    async def on_startup() -> None:
        """Register functions with the server on startup."""
        nonlocal heartbeat_task
        print(f"[Worker] Registering {len(functions)} functions with {server_url}...")
        await _register_functions(
            server_url, flowforge.app_id, functions, worker_url, flowforge.api_key
        )
        print(f"[Worker] Registration complete")

        # Start heartbeat loop
        function_ids = [fn.id for fn in functions]
        heartbeat_task = asyncio.create_task(
            _heartbeat_loop(server_url, function_ids, flowforge.api_key)
        )
        print(f"[Worker] Heartbeat started (every {HEARTBEAT_INTERVAL}s)")

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        """Clean up on shutdown."""
        nonlocal heartbeat_task
        if heartbeat_task:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
        print("[Worker] Shutdown complete")

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
