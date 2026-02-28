"""API-layer middleware for FlowForge.

This package contains middleware that belongs specifically at the HTTP API boundary:
security headers and structured request logging. It complements the infrastructure
middleware in ``flowforge_server.middleware`` (correlation IDs, rate limiting),
which operates at a lower level and is shared with non-API contexts.

Registration order in ``app.py`` matters — middlewares are applied inside-out
(last registered = outermost). Add API middleware after correlation middleware so
the correlation ID is available to the request logger.

Usage in ``api/app.py``::

    from flowforge_server.api.middleware import add_api_middleware
    add_api_middleware(app)
"""

from flowforge_server.api.middleware.security import SecurityHeadersMiddleware


def add_api_middleware(app: object) -> None:
    """Register all API-layer middleware on the FastAPI app.

    Call this after registering routers and the correlation middleware.
    """
    app.add_middleware(SecurityHeadersMiddleware)  # type: ignore[attr-defined]


__all__ = [
    "SecurityHeadersMiddleware",
    "add_api_middleware",
]
