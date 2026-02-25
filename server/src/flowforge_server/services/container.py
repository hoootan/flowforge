"""Dependency injection container for FlowForge services.

This module provides a centralized container for all service instances,
enabling proper lifecycle management and testability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from fastapi import Request

if TYPE_CHECKING:
    from flowforge_server.services.ai import AIService
    from flowforge_server.queue import FairQueue
    from flowforge_server.stream import RedisEventStream
    from flowforge_server.stream.pubsub import RunEventPubSub


@dataclass
class ServiceContainer:
    """
    Container holding all service instances.

    This container is initialized during application startup and stored
    in app.state.services. It provides clean dependency injection for
    route handlers and other components.

    Usage in routes:
        container = get_services(request)
        result = await container.ai_service.complete(...)
    """

    ai_service: "AIService"
    job_queue: "FairQueue"
    event_stream: "RedisEventStream"
    pubsub: "RunEventPubSub"

    # Optional flag to track initialization
    _initialized: bool = field(default=False, repr=False)

    async def initialize(self) -> None:
        """Initialize all services that require async setup."""
        if self._initialized:
            return

        # Initialize Redis connections for queue and stream
        # These are lazily connected on first use, but we can warm them up
        try:
            # Warm up queue connection
            await self.job_queue._get_client()
        except Exception:
            pass  # Will connect on first use

        try:
            # Warm up pubsub connection
            await self.pubsub._get_client()
        except Exception:
            pass  # Will connect on first use

        self._initialized = True

    async def close(self) -> None:
        """Close all service connections."""
        # Close queue connection
        if hasattr(self.job_queue, "_client") and self.job_queue._client:
            await self.job_queue._client.close()

        # Close event stream connection
        if hasattr(self.event_stream, "_client") and self.event_stream._client:
            await self.event_stream._client.close()

        # Close pubsub connection
        if hasattr(self.pubsub, "_client") and self.pubsub._client:
            await self.pubsub._client.close()

        self._initialized = False


def create_service_container() -> ServiceContainer:
    """
    Create a new service container with all services.

    This factory function creates and wires up all service instances.
    Should be called once during application startup.
    """
    from flowforge_server.services.ai import AIService
    from flowforge_server.queue import FairQueue
    from flowforge_server.stream import RedisEventStream
    from flowforge_server.stream.pubsub import RunEventPubSub

    from flowforge_server.services.providers import get_provider_registry

    ai_service = AIService()
    ai_service.provider_registry = get_provider_registry()

    return ServiceContainer(
        ai_service=ai_service,
        job_queue=FairQueue(),
        event_stream=RedisEventStream(),
        pubsub=RunEventPubSub(),
    )


def get_services(request: Request) -> ServiceContainer:
    """
    Get the service container from the request.

    This is a dependency function for FastAPI routes.

    Args:
        request: The FastAPI request object

    Returns:
        The ServiceContainer instance

    Raises:
        RuntimeError: If services are not initialized
    """
    services = getattr(request.app.state, "services", None)
    if services is None:
        raise RuntimeError(
            "Services not initialized. Ensure the application lifespan is properly configured."
        )
    return services


def get_ai_service(request: Request) -> "AIService":
    """Get the AI service from the request."""
    return get_services(request).ai_service


def get_job_queue(request: Request) -> "FairQueue":
    """Get the job queue from the request."""
    return get_services(request).job_queue


def get_event_stream(request: Request) -> "RedisEventStream":
    """Get the event stream from the request."""
    return get_services(request).event_stream


def get_pubsub(request: Request) -> "RunEventPubSub":
    """Get the pubsub from the request."""
    return get_services(request).pubsub
