"""Global error handlers for FlowForge API.

Provides centralized exception handling with:
- Error sanitization in production
- Correlation IDs for tracking
- Structured logging
"""

from __future__ import annotations

import traceback
import uuid
from typing import TYPE_CHECKING

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from flowforge_server.config import get_settings
from flowforge_server.logging import Loggers

if TYPE_CHECKING:
    from fastapi import FastAPI


# Header name for correlation ID
CORRELATION_ID_HEADER = "X-Correlation-ID"


def get_correlation_id(request: Request) -> str:
    """
    Get or generate a correlation ID for the request.

    If the client provides one via header, use it.
    Otherwise generate a new one.
    """
    correlation_id = request.headers.get(CORRELATION_ID_HEADER)
    if correlation_id:
        return correlation_id
    return str(uuid.uuid4())


def create_error_response(
    status_code: int,
    message: str,
    correlation_id: str,
    details: dict | None = None,
) -> JSONResponse:
    """Create a standardized error response."""
    content = {
        "error": {
            "message": message,
            "correlation_id": correlation_id,
        }
    }

    if details:
        content["error"]["details"] = details

    return JSONResponse(
        status_code=status_code,
        content=content,
        headers={CORRELATION_ID_HEADER: correlation_id},
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """
    Handle HTTP exceptions (raised by FastAPI/Starlette).

    These are expected errors (404, 401, 403, etc.) and their
    details are safe to return to clients.
    """
    correlation_id = get_correlation_id(request)
    log = Loggers.api()

    log.info(
        "http_exception",
        correlation_id=correlation_id,
        status_code=exc.status_code,
        detail=str(exc.detail),
        path=request.url.path,
        method=request.method,
    )

    # Extract headers if present
    headers = getattr(exc, "headers", None) or {}

    response = create_error_response(
        status_code=exc.status_code,
        message=str(exc.detail),
        correlation_id=correlation_id,
    )

    # Add any exception headers (like Retry-After for rate limits)
    for header, value in headers.items():
        response.headers[header] = value

    return response


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """
    Handle request validation errors.

    Provides clear feedback about what fields failed validation.
    """
    correlation_id = get_correlation_id(request)
    log = Loggers.api()
    settings = get_settings()

    # Extract validation errors
    errors = exc.errors()

    log.warning(
        "validation_error",
        correlation_id=correlation_id,
        path=request.url.path,
        method=request.method,
        error_count=len(errors),
    )

    # In development, include full validation details
    if settings.is_development:
        details = {"validation_errors": errors}
    else:
        # In production, simplify the error messages
        details = {
            "validation_errors": [
                {
                    "field": ".".join(str(loc) for loc in err.get("loc", [])),
                    "message": err.get("msg", "Invalid value"),
                }
                for err in errors
            ]
        }

    return create_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="Request validation failed",
        correlation_id=correlation_id,
        details=details,
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """
    Handle unhandled exceptions.

    In production: Returns safe generic message, logs full details.
    In development: Returns full exception details for debugging.
    """
    correlation_id = get_correlation_id(request)
    log = Loggers.api()
    settings = get_settings()

    # Always log the full exception server-side
    log.error(
        "unhandled_exception",
        correlation_id=correlation_id,
        path=request.url.path,
        method=request.method,
        exception_type=type(exc).__name__,
        exception_message=str(exc),
        traceback=traceback.format_exc(),
    )

    if settings.is_development or settings.debug:
        # In development, return full error details
        return create_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=str(exc),
            correlation_id=correlation_id,
            details={
                "exception_type": type(exc).__name__,
                "traceback": traceback.format_exc().split("\n"),
            },
        )

    # In production, return a safe generic message
    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="An internal error occurred. Please try again later.",
        correlation_id=correlation_id,
    )


def register_error_handlers(app: FastAPI) -> None:
    """
    Register all error handlers with the FastAPI application.

    Call this in your application factory after creating the app.
    """
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
