"""Correlation ID middleware for request tracing.

Adds correlation IDs to all requests for distributed tracing and debugging.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

if TYPE_CHECKING:
    from fastapi import FastAPI


# Context variable to store correlation ID for the current request
_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)

# Header name for correlation ID
CORRELATION_ID_HEADER = "X-Correlation-ID"


def get_correlation_id() -> str | None:
    """
    Get the current request's correlation ID.

    Can be called from anywhere in the request context to get the correlation ID.
    Returns None if called outside of a request context.
    """
    return _correlation_id.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID for the current request context."""
    _correlation_id.set(correlation_id)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds correlation IDs to all requests.

    - If the client provides X-Correlation-ID, use it
    - Otherwise, generate a new UUID
    - Store in context variable for logging
    - Add to response headers
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        # Get or generate correlation ID
        correlation_id = request.headers.get(CORRELATION_ID_HEADER)
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        # Store in context variable for access throughout the request
        set_correlation_id(correlation_id)

        # Store in request state for easy access
        request.state.correlation_id = correlation_id

        # Process request
        response = await call_next(request)

        # Add correlation ID to response headers
        response.headers[CORRELATION_ID_HEADER] = correlation_id

        return response


def add_correlation_middleware(app: FastAPI) -> None:
    """
    Add correlation ID middleware to a FastAPI application.

    Call this in your application factory after creating the app.
    """
    app.add_middleware(CorrelationIdMiddleware)
