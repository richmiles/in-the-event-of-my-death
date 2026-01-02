"""Discord webhook notification service."""

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger()


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
