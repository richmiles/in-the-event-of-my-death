"""
Request logging middleware with correlation ID support.

Generates a unique correlation ID for each request, binds it to the structlog
context, and logs request start/completion with timing information.

Privacy: Never logs IPs, authorization headers, or sensitive data.
"""

import secrets
import time

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


def generate_correlation_id() -> str:
    """Generate an 8-character correlation ID."""
    return secrets.token_hex(4)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs requests and adds correlation IDs.

    Logs:
    - request_started: method, path, correlation_id
    - request_completed: method, path, status_code, duration_ms, correlation_id

    Never logs:
    - IP addresses
    - Authorization headers
    - Query parameters (may contain tokens)
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        correlation_id = generate_correlation_id()
        start_time = time.perf_counter()

        # Bind correlation ID to structlog context for this request
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        logger = structlog.get_logger()

        # Log request start (path only, no query params)
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
        )

        try:
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log request completion
            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )

            # Add correlation ID to response header for debugging
            response.headers["X-Correlation-ID"] = correlation_id

            return response

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "request_failed",
                method=request.method,
                path=request.url.path,
                error=str(e),
                duration_ms=round(duration_ms, 2),
                exc_info=True,
            )
            raise
