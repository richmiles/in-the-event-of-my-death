"""Tests for the secret service functions."""

import base64
import secrets
from datetime import timedelta

import pytest

from app.services.secret_service import create_secret, delete_expired_secrets
from tests.test_utils import utcnow


@pytest.fixture
def sample_tokens():
    """Generate sample tokens for testing."""
    return {
        "edit_token": secrets.token_hex(32),
        "decrypt_token": secrets.token_hex(32),
    }


class TestDeleteExpiredSecrets:
    """Tests for the delete_expired_secrets function."""

    def test_delete_expired_secrets(self, db_session, sample_tokens):
        """Test that expired secrets are marked as deleted."""
        # Create test data
        iv = base64.b64encode(secrets.token_bytes(12)).decode()
        auth_tag = base64.b64encode(secrets.token_bytes(16)).decode()
        ciphertext = base64.b64encode(secrets.token_bytes(100)).decode()

        # Create an expired secret (expires in the past)
        unlock_at = utcnow() + timedelta(hours=1)
        expires_at = utcnow() - timedelta(hours=1)  # Already expired
        expired_secret = create_secret(
            db=db_session,
            ciphertext_b64=ciphertext,
            iv_b64=iv,
            auth_tag_b64=auth_tag,
            unlock_at=unlock_at,
            edit_token=sample_tokens["edit_token"],
            decrypt_token=sample_tokens["decrypt_token"],
            expires_at=expires_at,
        )

        # Verify it's not deleted yet
        assert expired_secret.is_deleted is False
        assert expired_secret.retrieved_at is None

        # Run the delete expired secrets function
        deleted_count = delete_expired_secrets(db_session)

        # Verify the secret was marked as deleted
        assert deleted_count == 1
        db_session.refresh(expired_secret)
        assert expired_secret.is_deleted is True

    def test_dont_delete_non_expired_secrets(self, db_session, sample_tokens):
        """Test that non-expired secrets are not marked as deleted."""
        # Create test data
        iv = base64.b64encode(secrets.token_bytes(12)).decode()
        auth_tag = base64.b64encode(secrets.token_bytes(16)).decode()
        ciphertext = base64.b64encode(secrets.token_bytes(100)).decode()

        # Create a non-expired secret
        unlock_at = utcnow() + timedelta(hours=1)
        expires_at = utcnow() + timedelta(days=2)  # Not expired
        non_expired_secret = create_secret(
            db=db_session,
            ciphertext_b64=ciphertext,
            iv_b64=iv,
            auth_tag_b64=auth_tag,
            unlock_at=unlock_at,
            edit_token=sample_tokens["edit_token"],
            decrypt_token=sample_tokens["decrypt_token"],
            expires_at=expires_at,
        )

        # Run the delete expired secrets function
        deleted_count = delete_expired_secrets(db_session)

        # Verify the secret was not deleted
        assert deleted_count == 0
        db_session.refresh(non_expired_secret)
        assert non_expired_secret.is_deleted is False

    def test_dont_delete_secrets_without_expires_at(self, db_session, sample_tokens):
        """Test that secrets without expires_at are not marked as deleted."""
        # Create test data
        iv = base64.b64encode(secrets.token_bytes(12)).decode()
        auth_tag = base64.b64encode(secrets.token_bytes(16)).decode()
        ciphertext = base64.b64encode(secrets.token_bytes(100)).decode()

        # Create a secret without expires_at
        unlock_at = utcnow() + timedelta(hours=1)
        secret_no_expiry = create_secret(
            db=db_session,
            ciphertext_b64=ciphertext,
            iv_b64=iv,
            auth_tag_b64=auth_tag,
            unlock_at=unlock_at,
            edit_token=sample_tokens["edit_token"],
            decrypt_token=sample_tokens["decrypt_token"],
            expires_at=None,
        )

        # Run the delete expired secrets function
        deleted_count = delete_expired_secrets(db_session)

        # Verify the secret was not deleted
        assert deleted_count == 0
        db_session.refresh(secret_no_expiry)
        assert secret_no_expiry.is_deleted is False

    def test_dont_delete_already_retrieved_secrets(self, db_session, sample_tokens):
        """Test that already retrieved secrets are not marked as deleted again."""
        # Create test data
        iv = base64.b64encode(secrets.token_bytes(12)).decode()
        auth_tag = base64.b64encode(secrets.token_bytes(16)).decode()
        ciphertext = base64.b64encode(secrets.token_bytes(100)).decode()

        # Create an expired secret that has already been retrieved
        unlock_at = utcnow() - timedelta(hours=2)  # Unlocked in the past
        expires_at = utcnow() - timedelta(hours=1)  # Expired
        retrieved_secret = create_secret(
            db=db_session,
            ciphertext_b64=ciphertext,
            iv_b64=iv,
            auth_tag_b64=auth_tag,
            unlock_at=unlock_at,
            edit_token=sample_tokens["edit_token"],
            decrypt_token=sample_tokens["decrypt_token"],
            expires_at=expires_at,
        )

        # Mark as retrieved
        retrieved_secret.retrieved_at = utcnow() - timedelta(minutes=30)
        db_session.commit()

        # Run the delete expired secrets function
        deleted_count = delete_expired_secrets(db_session)

        # Verify the count is 0 (already retrieved secrets should not be counted)
        assert deleted_count == 0
