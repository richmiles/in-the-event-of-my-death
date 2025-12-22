"""Tests for the secret service functions."""

import base64
import secrets
from datetime import timedelta

import pytest

from app.services.secret_service import clear_expired_secrets, create_secret
from tests.test_utils import utcnow


@pytest.fixture
def sample_tokens():
    """Generate sample tokens for testing."""
    return {
        "edit_token": secrets.token_hex(32),
        "decrypt_token": secrets.token_hex(32),
    }


class TestClearExpiredSecrets:
    """Tests for the clear_expired_secrets function."""

    def test_clear_expired_secrets(self, db_session, sample_tokens):
        """Test that expired secrets have their ciphertext cleared."""
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

        # Verify it's not cleared yet
        assert expired_secret.cleared_at is None
        assert expired_secret.ciphertext is not None

        # Run the clear expired secrets function
        cleared_count = clear_expired_secrets(db_session)

        # Verify the secret was cleared
        assert cleared_count == 1
        db_session.refresh(expired_secret)
        assert expired_secret.cleared_at is not None
        assert expired_secret.ciphertext is None
        assert expired_secret.iv is None
        assert expired_secret.auth_tag is None
        # Metadata should be preserved (row not deleted)
        assert expired_secret.id is not None
        assert expired_secret.unlock_at is not None
        assert expired_secret.expires_at is not None
        assert expired_secret.created_at is not None

    def test_clear_retrieved_secrets(self, db_session, sample_tokens):
        """Test that retrieved secrets have their ciphertext cleared."""
        # Create test data
        iv = base64.b64encode(secrets.token_bytes(12)).decode()
        auth_tag = base64.b64encode(secrets.token_bytes(16)).decode()
        ciphertext = base64.b64encode(secrets.token_bytes(100)).decode()

        # Create a secret that has been retrieved (not yet expired)
        unlock_at = utcnow() - timedelta(hours=1)
        expires_at = utcnow() + timedelta(days=30)  # Not expired
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

        # Mark as retrieved (simulating what retrieve_secret does)
        retrieved_secret.retrieved_at = utcnow() - timedelta(minutes=30)
        retrieved_secret.is_deleted = True
        db_session.commit()

        # Verify it's not cleared yet
        assert retrieved_secret.cleared_at is None
        assert retrieved_secret.ciphertext is not None

        # Run the clear function
        cleared_count = clear_expired_secrets(db_session)

        # Verify the secret was cleared
        assert cleared_count == 1
        db_session.refresh(retrieved_secret)
        assert retrieved_secret.cleared_at is not None
        assert retrieved_secret.ciphertext is None
        assert retrieved_secret.iv is None
        assert retrieved_secret.auth_tag is None
        # Metadata should be preserved (row not deleted)
        assert retrieved_secret.id is not None
        assert retrieved_secret.retrieved_at is not None

    def test_dont_clear_non_expired_non_retrieved_secrets(self, db_session, sample_tokens):
        """Test that active secrets (not expired, not retrieved) are not cleared."""
        # Create test data
        iv = base64.b64encode(secrets.token_bytes(12)).decode()
        auth_tag = base64.b64encode(secrets.token_bytes(16)).decode()
        ciphertext = base64.b64encode(secrets.token_bytes(100)).decode()

        # Create a non-expired, non-retrieved secret
        unlock_at = utcnow() + timedelta(hours=1)
        expires_at = utcnow() + timedelta(days=2)  # Not expired
        active_secret = create_secret(
            db=db_session,
            ciphertext_b64=ciphertext,
            iv_b64=iv,
            auth_tag_b64=auth_tag,
            unlock_at=unlock_at,
            edit_token=sample_tokens["edit_token"],
            decrypt_token=sample_tokens["decrypt_token"],
            expires_at=expires_at,
        )

        # Run the clear function
        cleared_count = clear_expired_secrets(db_session)

        # Verify the secret was not cleared
        assert cleared_count == 0
        db_session.refresh(active_secret)
        assert active_secret.cleared_at is None
        assert active_secret.ciphertext is not None

    def test_dont_clear_already_cleared_secrets(self, db_session, sample_tokens):
        """Test that already cleared secrets are not processed again."""
        # Create test data
        iv = base64.b64encode(secrets.token_bytes(12)).decode()
        auth_tag = base64.b64encode(secrets.token_bytes(16)).decode()
        ciphertext = base64.b64encode(secrets.token_bytes(100)).decode()

        # Create an expired secret
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

        # Clear it once
        cleared_count = clear_expired_secrets(db_session)
        assert cleared_count == 1
        db_session.refresh(expired_secret)
        first_cleared_at = expired_secret.cleared_at

        # Try to clear again
        cleared_count = clear_expired_secrets(db_session)

        # Verify nothing was cleared (already processed)
        assert cleared_count == 0
        db_session.refresh(expired_secret)
        assert expired_secret.cleared_at == first_cleared_at
