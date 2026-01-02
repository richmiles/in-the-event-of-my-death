"""Discord webhook notification service."""

import threading
from datetime import UTC, datetime, timedelta

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger()

# Rate limiting for error alerts to prevent alert storms
_last_alert_time: datetime | None = None
_alert_cooldown = timedelta(seconds=30)
_alert_lock = threading.Lock()


async def send_feedback_notification(message: str, email: str | None) -> bool:
    """
    Send feedback notification to Discord webhook.

    Returns True if notification was sent successfully, False otherwise.
    Failures are logged but don't raise exceptions - feedback should still succeed.
    """
    webhook_url = settings.discord_feedback_webhook_url

    if not webhook_url:
        logger.warning("discord_webhook_not_configured", webhook_type="feedback")
        return False

    contact = email if email else "not provided"
    content = f"**New Feedback**\n\n{message}\n\n**Contact:** {contact}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                json={"content": content},
                timeout=10.0,
            )
            response.raise_for_status()
            logger.info("discord_notification_sent", webhook_type="feedback")
            return True
    except httpx.HTTPStatusError as e:
        logger.error(
            "discord_webhook_error",
            webhook_type="feedback",
            status_code=e.response.status_code,
        )
        return False
    except httpx.RequestError as e:
        logger.error(
            "discord_webhook_request_error",
            webhook_type="feedback",
            error=str(e),
        )
        return False


def _should_send_alert() -> bool:
    """Check if we should send an alert (rate limiting)."""
    global _last_alert_time
    with _alert_lock:
        now = datetime.now(UTC)
        if _last_alert_time and (now - _last_alert_time) < _alert_cooldown:
            return False
        _last_alert_time = now
        return True


def reset_alert_rate_limit() -> None:
    """Reset the rate limit state. Used in tests."""
    global _last_alert_time
    with _alert_lock:
        _last_alert_time = None


async def send_error_alert(
    error_type: str,
    message: str,
    *,
    path: str | None = None,
    correlation_id: str | None = None,
    status_code: int | None = None,
    context: dict | None = None,
) -> bool:
    """
    Send error alert to Discord webhook.

    Returns True if notification was sent successfully, False otherwise.
    Failures are logged but don't raise exceptions.
    Rate-limited to prevent alert storms (max 1 alert per 30 seconds).
    """
    webhook_url = settings.discord_alerts_webhook_url

    if not webhook_url:
        logger.debug("discord_alerts_webhook_not_configured")
        return False

    if not _should_send_alert():
        logger.info("discord_alert_rate_limited", error_type=error_type)
        return False

    # Build embed fields
    fields = [{"name": "Error Type", "value": error_type, "inline": True}]
    if status_code:
        fields.append({"name": "Status", "value": str(status_code), "inline": True})
    if path:
        fields.append({"name": "Path", "value": path, "inline": True})
    if correlation_id:
        fields.append({"name": "Correlation ID", "value": correlation_id, "inline": True})
    if message:
        # Truncate long messages
        truncated = message[:500] + "..." if len(message) > 500 else message
        fields.append({"name": "Message", "value": truncated, "inline": False})
    if context:
        for key, value in context.items():
            str_value = str(value)
            truncated = str_value[:200] + "..." if len(str_value) > 200 else str_value
            fields.append({"name": key, "value": truncated, "inline": True})

    payload = {
        "embeds": [
            {
                "title": "Server Error Alert",
                "color": 15158332,  # Red
                "fields": fields,
                "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            }
        ]
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=payload, timeout=10.0)
            response.raise_for_status()
            logger.info("discord_error_alert_sent", error_type=error_type)
            return True
    except httpx.HTTPStatusError as e:
        logger.error(
            "discord_alert_webhook_error",
            error_type=error_type,
            status_code=e.response.status_code,
        )
        return False
    except httpx.RequestError as e:
        logger.error(
            "discord_alert_request_error",
            error_type=error_type,
            error=str(e),
        )
        return False


def send_error_alert_sync(
    error_type: str,
    message: str,
    *,
    path: str | None = None,
    correlation_id: str | None = None,
    status_code: int | None = None,
    context: dict | None = None,
) -> bool:
    """
    Synchronous version of send_error_alert for scheduler jobs.

    Uses httpx synchronously to avoid asyncio.run() complexity.
    """
    webhook_url = settings.discord_alerts_webhook_url

    if not webhook_url:
        logger.debug("discord_alerts_webhook_not_configured")
        return False

    if not _should_send_alert():
        logger.info("discord_alert_rate_limited", error_type=error_type)
        return False

    # Build embed fields
    fields = [{"name": "Error Type", "value": error_type, "inline": True}]
    if status_code:
        fields.append({"name": "Status", "value": str(status_code), "inline": True})
    if path:
        fields.append({"name": "Path", "value": path, "inline": True})
    if correlation_id:
        fields.append({"name": "Correlation ID", "value": correlation_id, "inline": True})
    if message:
        truncated = message[:500] + "..." if len(message) > 500 else message
        fields.append({"name": "Message", "value": truncated, "inline": False})
    if context:
        for key, value in context.items():
            str_value = str(value)
            truncated = str_value[:200] + "..." if len(str_value) > 200 else str_value
            fields.append({"name": key, "value": truncated, "inline": True})

    payload = {
        "embeds": [
            {
                "title": "Server Error Alert",
                "color": 15158332,
                "fields": fields,
                "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            }
        ]
    }

    try:
        with httpx.Client() as client:
            response = client.post(webhook_url, json=payload, timeout=10.0)
            response.raise_for_status()
            logger.info("discord_error_alert_sent", error_type=error_type)
            return True
    except httpx.HTTPStatusError as e:
        logger.error(
            "discord_alert_webhook_error",
            error_type=error_type,
            status_code=e.response.status_code,
        )
        return False
    except httpx.RequestError as e:
        logger.error(
            "discord_alert_request_error",
            error_type=error_type,
            error=str(e),
        )
        return False
