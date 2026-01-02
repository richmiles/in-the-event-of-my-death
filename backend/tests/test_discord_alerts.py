"""Tests for Discord error alert functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.discord_service import (
    reset_alert_rate_limit,
    send_error_alert,
    send_error_alert_sync,
)


class TestDiscordErrorAlerts:
    """Unit tests for send_error_alert."""

    @pytest.fixture(autouse=True)
    def reset_rate_limit(self):
        """Reset rate limit state before each test."""
        reset_alert_rate_limit()

    @pytest.mark.asyncio
    async def test_send_error_alert_success(self):
        """Test successful error alert notification."""
        with patch("app.services.discord_service.settings") as mock_settings:
            mock_settings.discord_alerts_webhook_url = "https://discord.com/webhook"

            with patch("app.services.discord_service.httpx.AsyncClient") as mock_client:
                mock_response = AsyncMock()
                mock_response.raise_for_status = AsyncMock()
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    return_value=mock_response
                )

                result = await send_error_alert(
                    error_type="ValueError",
                    message="Something went wrong",
                    path="/api/v1/secrets",
                    correlation_id="abc12345",
                    status_code=500,
                )

                assert result is True
                # Verify the webhook was called with embed format
                call_args = mock_client.return_value.__aenter__.return_value.post.call_args
                payload = call_args.kwargs["json"]
                assert "embeds" in payload
                assert payload["embeds"][0]["title"] == "Server Error Alert"
                assert payload["embeds"][0]["color"] == 15158332  # Red

    @pytest.mark.asyncio
    async def test_send_error_alert_not_configured(self):
        """Test when webhook URL is not configured."""
        with patch("app.services.discord_service.settings") as mock_settings:
            mock_settings.discord_alerts_webhook_url = None

            result = await send_error_alert(
                error_type="ValueError",
                message="Something went wrong",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_send_error_alert_rate_limited(self):
        """Test that second alert within cooldown is rate limited."""
        with patch("app.services.discord_service.settings") as mock_settings:
            mock_settings.discord_alerts_webhook_url = "https://discord.com/webhook"

            with patch("app.services.discord_service.httpx.AsyncClient") as mock_client:
                mock_response = AsyncMock()
                mock_response.raise_for_status = AsyncMock()
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    return_value=mock_response
                )

                # First alert should succeed
                result1 = await send_error_alert(
                    error_type="Error1",
                    message="First error",
                )
                assert result1 is True

                # Second alert should be rate limited
                result2 = await send_error_alert(
                    error_type="Error2",
                    message="Second error",
                )
                assert result2 is False

                # Verify only one webhook call was made
                assert mock_client.return_value.__aenter__.return_value.post.call_count == 1

    @pytest.mark.asyncio
    async def test_send_error_alert_failure_graceful(self):
        """Test that webhook failure doesn't raise exception."""
        with patch("app.services.discord_service.settings") as mock_settings:
            mock_settings.discord_alerts_webhook_url = "https://discord.com/webhook"

            with patch("app.services.discord_service.httpx.AsyncClient") as mock_client:
                mock_request = MagicMock()
                mock_response = MagicMock()
                mock_response.status_code = 500

                def raise_for_status():
                    raise httpx.HTTPStatusError(
                        "Server error", request=mock_request, response=mock_response
                    )

                mock_response.raise_for_status = raise_for_status

                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    return_value=mock_response
                )

                # Should not raise, just return False
                result = await send_error_alert(
                    error_type="ValueError",
                    message="Something went wrong",
                )

                assert result is False

    @pytest.mark.asyncio
    async def test_send_error_alert_with_context(self):
        """Test alert with additional context fields."""
        with patch("app.services.discord_service.settings") as mock_settings:
            mock_settings.discord_alerts_webhook_url = "https://discord.com/webhook"

            with patch("app.services.discord_service.httpx.AsyncClient") as mock_client:
                mock_response = AsyncMock()
                mock_response.raise_for_status = AsyncMock()
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    return_value=mock_response
                )

                result = await send_error_alert(
                    error_type="Scheduler Job Failed",
                    message="Database connection error",
                    context={"job_name": "cleanup_secrets"},
                )

                assert result is True
                call_args = mock_client.return_value.__aenter__.return_value.post.call_args
                payload = call_args.kwargs["json"]
                fields = payload["embeds"][0]["fields"]
                field_names = [f["name"] for f in fields]
                assert "job_name" in field_names

    @pytest.mark.asyncio
    async def test_send_error_alert_truncates_long_message(self):
        """Test that long messages are truncated."""
        with patch("app.services.discord_service.settings") as mock_settings:
            mock_settings.discord_alerts_webhook_url = "https://discord.com/webhook"

            with patch("app.services.discord_service.httpx.AsyncClient") as mock_client:
                mock_response = AsyncMock()
                mock_response.raise_for_status = AsyncMock()
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    return_value=mock_response
                )

                long_message = "x" * 1000

                result = await send_error_alert(
                    error_type="ValueError",
                    message=long_message,
                )

                assert result is True
                call_args = mock_client.return_value.__aenter__.return_value.post.call_args
                payload = call_args.kwargs["json"]
                message_field = next(
                    f for f in payload["embeds"][0]["fields"] if f["name"] == "Message"
                )
                # Should be truncated to 500 chars + "..."
                assert len(message_field["value"]) == 503
                assert message_field["value"].endswith("...")

    def test_send_error_alert_sync_wrapper(self):
        """Test sync wrapper for scheduler jobs."""
        with patch("app.services.discord_service.settings") as mock_settings:
            mock_settings.discord_alerts_webhook_url = "https://discord.com/webhook"

            with patch("app.services.discord_service.httpx.Client") as mock_client:
                mock_response = MagicMock()
                mock_response.raise_for_status = MagicMock()
                mock_client.return_value.__enter__.return_value.post = MagicMock(
                    return_value=mock_response
                )

                result = send_error_alert_sync(
                    error_type="Scheduler Job Failed",
                    message="Cleanup failed",
                    context={"job_name": "cleanup_secrets"},
                )

                assert result is True


class TestExceptionHandlerAlerts:
    """Unit tests for exception handlers calling send_error_alert."""

    @pytest.fixture(autouse=True)
    def reset_rate_limit(self):
        """Reset rate limit state before each test."""
        reset_alert_rate_limit()

    @pytest.mark.asyncio
    async def test_500_exception_triggers_alert(self):
        """Test that unhandled exceptions trigger Discord alerts."""
        from unittest.mock import MagicMock

        from fastapi import Request

        from app.main import add_correlation_id_to_errors

        # Create a fake request
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/v1/secrets"

        # Patch the imported send_error_alert in main module
        with patch("app.main.send_error_alert", new_callable=AsyncMock) as mock_alert:
            mock_alert.return_value = True

            # Mock structlog context to return a correlation ID
            with patch("structlog.contextvars.get_contextvars") as mock_ctx:
                mock_ctx.return_value = {"correlation_id": "test-corr-id"}

                # Call the handler directly with a RuntimeError
                response = await add_correlation_id_to_errors(
                    mock_request, RuntimeError("Database failed")
                )

                # Verify alert was called
                mock_alert.assert_awaited_once()
                call_kwargs = mock_alert.call_args.kwargs
                assert call_kwargs["status_code"] == 500
                assert call_kwargs["path"] == "/api/v1/secrets"
                assert call_kwargs["correlation_id"] == "test-corr-id"
                assert "RuntimeError" in call_kwargs["error_type"]

                # Verify response
                assert response.status_code == 500
                assert response.headers["x-correlation-id"] == "test-corr-id"

    @pytest.mark.asyncio
    async def test_429_rate_limit_triggers_alert(self):
        """Test that rate limit exceeded triggers Discord alerts."""
        from unittest.mock import MagicMock

        from fastapi import Request

        from app.main import rate_limit_exceeded_handler

        # Create a fake request
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/v1/challenges"

        # Create a mock rate limit exception with detail attribute
        exc = MagicMock()
        exc.detail = "5 per 1 minute"

        with patch("app.main.send_error_alert", new_callable=AsyncMock) as mock_alert:
            mock_alert.return_value = True

            with patch("structlog.contextvars.get_contextvars") as mock_ctx:
                mock_ctx.return_value = {"correlation_id": "rate-limit-corr"}

                response = await rate_limit_exceeded_handler(mock_request, exc)

                # Verify alert was called
                mock_alert.assert_awaited_once()
                call_kwargs = mock_alert.call_args.kwargs
                assert call_kwargs["status_code"] == 429
                assert call_kwargs["path"] == "/api/v1/challenges"
                assert call_kwargs["correlation_id"] == "rate-limit-corr"
                assert "Rate Limit Exceeded" in call_kwargs["error_type"]

                # Verify response
                assert response.status_code == 429
                assert response.headers["retry-after"] == "60"

    @pytest.mark.asyncio
    async def test_5xx_http_exception_triggers_alert(self):
        """Test that 5xx HTTPExceptions trigger alerts."""
        from unittest.mock import MagicMock

        from fastapi import HTTPException, Request

        from app.main import add_correlation_id_to_errors

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/v1/secrets"

        exc = HTTPException(status_code=503, detail="Service Unavailable")

        with patch("app.main.send_error_alert", new_callable=AsyncMock) as mock_alert:
            mock_alert.return_value = True

            with patch("structlog.contextvars.get_contextvars") as mock_ctx:
                mock_ctx.return_value = {"correlation_id": "http-exc-corr"}

                response = await add_correlation_id_to_errors(mock_request, exc)

                # Verify alert was called for 5xx
                mock_alert.assert_awaited_once()
                assert mock_alert.call_args.kwargs["status_code"] == 503

                assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_4xx_http_exception_does_not_trigger_alert(self):
        """Test that 4xx HTTPExceptions do NOT trigger alerts."""
        from unittest.mock import MagicMock

        from fastapi import HTTPException, Request

        from app.main import add_correlation_id_to_errors

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/v1/secrets/notfound"

        exc = HTTPException(status_code=404, detail="Not Found")

        with patch("app.main.send_error_alert", new_callable=AsyncMock) as mock_alert:
            with patch("structlog.contextvars.get_contextvars") as mock_ctx:
                mock_ctx.return_value = {"correlation_id": "not-found-corr"}

                response = await add_correlation_id_to_errors(mock_request, exc)

                # Alert should NOT be called for 4xx
                mock_alert.assert_not_awaited()

                # But response should still be correct
                assert response.status_code == 404
