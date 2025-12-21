"""Shared test utilities."""

from datetime import UTC, datetime


def utcnow():
    """Get current UTC time as naive datetime."""
    return datetime.now(UTC).replace(tzinfo=None)
