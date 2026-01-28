"""Main entry point for FlowForge server."""

import uvicorn

from flowforge_server.api.app import app
from flowforge_server.config import get_settings


def run() -> None:
    """Run the FlowForge server."""
    settings = get_settings()

    uvicorn.run(
        "flowforge_server.api.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
        workers=settings.workers if not settings.is_development else 1,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    run()
