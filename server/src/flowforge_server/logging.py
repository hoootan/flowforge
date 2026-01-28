"""Structured logging configuration for FlowForge.

This module configures structlog for consistent, structured logging
across all FlowForge services.
"""

import logging
import sys
from typing import Any

import structlog
from structlog.types import Processor

from flowforge_server.config import get_settings


def configure_logging() -> None:
    """
    Configure structlog for the application.

    In development mode, logs are formatted for console readability.
    In production mode, logs are output as JSON for parsing by log aggregators.
    """
    settings = get_settings()

    # Set up standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
    )

    # Configure shared processors
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if settings.log_format == "json":
        # Production: JSON output
        processors: list[Processor] = [
            *shared_processors,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Development: Pretty console output
        processors = [
            *shared_processors,
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Optional logger name (typically __name__)

    Returns:
        A configured structlog BoundLogger
    """
    logger = structlog.get_logger()
    if name:
        logger = logger.bind(logger=name)
    return logger


# Pre-configured loggers for common components
class Loggers:
    """Pre-configured logger instances for FlowForge components."""

    @staticmethod
    def api() -> structlog.BoundLogger:
        """Logger for API routes."""
        return get_logger("flowforge.api")

    @staticmethod
    def executor() -> structlog.BoundLogger:
        """Logger for job executor."""
        return get_logger("flowforge.executor")

    @staticmethod
    def inline_executor() -> structlog.BoundLogger:
        """Logger for inline function executor."""
        return get_logger("flowforge.inline_executor")

    @staticmethod
    def ai() -> structlog.BoundLogger:
        """Logger for AI service."""
        return get_logger("flowforge.ai")

    @staticmethod
    def queue() -> structlog.BoundLogger:
        """Logger for job queue."""
        return get_logger("flowforge.queue")

    @staticmethod
    def stream() -> structlog.BoundLogger:
        """Logger for event stream."""
        return get_logger("flowforge.stream")

    @staticmethod
    def db() -> structlog.BoundLogger:
        """Logger for database operations."""
        return get_logger("flowforge.db")

    @staticmethod
    def tools() -> structlog.BoundLogger:
        """Logger for tool execution."""
        return get_logger("flowforge.tools")


# Convenience function for quick logging
def log_event(
    event: str,
    level: str = "info",
    **context: Any,
) -> None:
    """
    Log an event with context.

    This is a convenience function for quick event logging
    without needing to get a logger instance.

    Args:
        event: The event name/description
        level: Log level (debug, info, warning, error)
        **context: Additional context to include in the log
    """
    logger = get_logger()
    log_method = getattr(logger, level, logger.info)
    log_method(event, **context)
