"""FastAPI application factory."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from flowforge_server.config import get_settings
from flowforge_server.db import init_db, close_db, run_migrations
from flowforge_server.services.seed import run_all_seeds
from flowforge_server.services.container import create_service_container
from flowforge_server.logging import configure_logging, Loggers
from flowforge_server.api.routes import (
    events_router,
    functions_router,
    runs_router,
    health_router,
    approvals_router,
    stream_router,
    tools_router,
    auth_router,
    users_router,
    stats_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    # Configure logging first
    configure_logging()
    log = Loggers.api()

    # Startup
    settings = get_settings()
    log.info("starting_application", env=settings.env)

    if settings.is_development:
        # Initialize database tables in development
        await init_db()

    # Run any pending migrations
    await run_migrations()

    # Seed built-in tools and default data
    await run_all_seeds()

    # Initialize service container
    services = create_service_container()
    await services.initialize()
    app.state.services = services

    log.info("application_started")

    yield

    # Shutdown
    log.info("shutting_down_application")
    await services.close()
    await close_db()
    log.info("application_stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    # OpenAPI tags for better documentation organization
    tags_metadata = [
        {
            "name": "health",
            "description": "Health check endpoints",
        },
        {
            "name": "events",
            "description": "Event ingestion - trigger workflows by sending events",
        },
        {
            "name": "functions",
            "description": "Function management - register and configure workflow functions (both worker and serverless modes)",
        },
        {
            "name": "tools",
            "description": "Tool management - manage built-in and custom tools for agent-based functions",
        },
        {
            "name": "runs",
            "description": "Run management - view and control workflow executions",
        },
        {
            "name": "approvals",
            "description": "Human-in-the-Loop (HITL) - approve or reject tool calls that require human approval",
        },
        {
            "name": "stream",
            "description": "Real-time streaming - SSE endpoints for live run progress",
        },
        {
            "name": "auth",
            "description": "Authentication - API key management and token exchange",
        },
        {
            "name": "users",
            "description": "User management - dashboard user authentication and administration",
        },
        {
            "name": "stats",
            "description": "Dashboard statistics - aggregated metrics for the dashboard",
        },
    ]

    app = FastAPI(
        title="FlowForge API",
        description="""
## FlowForge - AI Workflow Orchestration Platform

FlowForge provides durable execution for AI-powered workflows with:

### Features
- **Serverless Functions**: Define agent-based functions via API (no worker needed)
- **Worker Functions**: Register functions from your own worker process
- **Built-in Tools**: Pre-configured tools for web search, image generation, social posting
- **Custom Tools**: Add your own tools with custom Python code
- **Human-in-the-Loop**: Tools can require human approval before execution
- **Real-time Streaming**: SSE support for live progress updates
- **Durable Execution**: Automatic retries, checkpointing, and recovery

### Execution Modes
1. **Serverless (Inline)**: Functions defined via API, executed internally by FlowForge
2. **Worker Mode**: Functions defined in code, executed by your worker process

### Quick Start
1. Create tools via `POST /api/v1/tools` (or use built-in tools)
2. Create a serverless function via `POST /api/v1/functions/inline`
3. Trigger via `POST /api/v1/events`
4. Stream progress via `GET /api/v1/runs/{id}/stream`
        """,
        version="0.1.0",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        openapi_tags=tags_metadata,
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(events_router, prefix="/api/v1")
    app.include_router(functions_router, prefix="/api/v1")
    app.include_router(runs_router, prefix="/api/v1")
    app.include_router(approvals_router, prefix="/api/v1")
    app.include_router(stream_router, prefix="/api/v1")
    app.include_router(tools_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(users_router, prefix="/api/v1")
    app.include_router(stats_router, prefix="/api/v1")

    return app


# Create default app instance
app = create_app()
