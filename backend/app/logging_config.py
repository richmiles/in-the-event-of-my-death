"""
Structured logging configuration using structlog.

Provides JSON output in production, pretty console output in development.
Follows 12-factor app pattern: logs to stdout, process manager handles persistence.
"""

import logging
import sys

import structlog

from app.config import settings


def setup_logging() -> None:
    """
    Configure structlog and stdlib logging integration.

    Call this once at application startup.
    """
    # Determine output format based on settings
    if settings.log_format == "json":
        # Production: JSON lines for log aggregation
        renderer = structlog.processors.JSONRenderer()
    else:
        # Development: Pretty console output
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    # Configure structlog
    structlog.configure(
        processors=[
            # Add log level to event dict
            structlog.stdlib.add_log_level,
            # Add timestamp
            structlog.processors.TimeStamper(fmt="iso"),
            # If running in an async context, add async info
            structlog.contextvars.merge_contextvars,
            # Process stack info if present
            structlog.processors.StackInfoRenderer(),
            # Format exceptions
            structlog.processors.format_exc_info,
            # Render to final format
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging to use structlog (for APScheduler, SQLAlchemy, etc.)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.INFO)


def get_logger(name: str | None = None):
    """
    Get a structlog logger instance.

    Args:
        name: Optional logger name for context

    Returns:
        Configured structlog logger
    """
    logger = structlog.get_logger()
    if name:
        logger = logger.bind(logger_name=name)
    return logger
