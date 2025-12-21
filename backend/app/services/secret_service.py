import base64
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.secret import Secret
from app.services.crypto_utils import hash_token, verify_token


def create_secret(
    db: Session,
    ciphertext_b64: str,
    iv_b64: str,
    auth_tag_b64: str,
    unlock_at: datetime,
    edit_token: str,
    decrypt_token: str,
    expires_at: datetime | None = None,
) -> Secret:
    """
    Create a new secret with hashed tokens.

    The tokens are hashed with Argon2id before storage.
    """
    ciphertext = base64.b64decode(ciphertext_b64)
    iv = base64.b64decode(iv_b64)
    auth_tag = base64.b64decode(auth_tag_b64)

    secret = Secret(
        ciphertext=ciphertext,
        iv=iv,
        auth_tag=auth_tag,
        unlock_at=unlock_at,
        expires_at=expires_at,
        edit_token_hash=hash_token(edit_token),
        decrypt_token_hash=hash_token(decrypt_token),
        ciphertext_size=len(ciphertext),
    )

    db.add(secret)
    db.commit()
    db.refresh(secret)

    return secret


def find_secret_by_edit_token(db: Session, edit_token: str) -> Secret | None:
    """Find a secret by its edit token (verifies hash)."""
    # We need to iterate through secrets since we can't directly query by token
    # In production, consider adding a token prefix/identifier for faster lookup
    secrets = db.query(Secret).filter(Secret.is_deleted == False).all()  # noqa: E712

    for secret in secrets:
        if verify_token(edit_token, secret.edit_token_hash):
            return secret

    return None


def find_secret_by_decrypt_token(db: Session, decrypt_token: str) -> Secret | None:
    """Find a secret by its decrypt token (verifies hash)."""
    secrets = db.query(Secret).filter(Secret.is_deleted == False).all()  # noqa: E712

    for secret in secrets:
        if verify_token(decrypt_token, secret.decrypt_token_hash):
            return secret

    return None


def extend_unlock_date(db: Session, secret: Secret, new_unlock_at: datetime) -> Secret:
    """
    Extend the unlock date of a secret.

    The new date must be after the current unlock date.
    """
    if new_unlock_at <= secret.unlock_at:
        raise ValueError("New unlock date must be after current unlock date")

    if secret.retrieved_at is not None:
        raise ValueError("Cannot edit a secret that has already been retrieved")

    if datetime.now(UTC).replace(tzinfo=None) >= secret.unlock_at:
        raise ValueError("Cannot edit a secret that has already unlocked")

    secret.unlock_at = new_unlock_at
    db.commit()
    db.refresh(secret)

    return secret


def retrieve_secret(db: Session, secret: Secret) -> dict:
    """
    Retrieve a secret's encrypted content.

    This is a one-time operation. After retrieval, the secret is marked for deletion.
    """
    now = datetime.now(UTC).replace(tzinfo=None)

    # Check if unlocked
    if now < secret.unlock_at:
        return {
            "status": "pending",
            "unlock_at": secret.unlock_at,
            "message": "Secret not yet available",
        }

    # Check if already retrieved
    if secret.retrieved_at is not None:
        return {
            "status": "retrieved",
            "message": "This secret has already been retrieved and is no longer available",
        }

    # Mark as retrieved and prepare for deletion
    secret.retrieved_at = now
    secret.is_deleted = True
    db.commit()

    return {
        "status": "available",
        "ciphertext": base64.b64encode(secret.ciphertext).decode(),
        "iv": base64.b64encode(secret.iv).decode(),
        "auth_tag": base64.b64encode(secret.auth_tag).decode(),
        "retrieved_at": secret.retrieved_at,
        "message": "This secret has been deleted and cannot be retrieved again.",
    }


def get_secret_status(db: Session, secret: Secret) -> dict:
    """
    Get the status of a secret without triggering one-time deletion.
    """
    now = datetime.now(UTC).replace(tzinfo=None)

    if secret.retrieved_at is not None:
        return {
            "exists": True,
            "status": "retrieved",
            "unlock_at": secret.unlock_at,
            "expires_at": secret.expires_at,
        }

    if now >= secret.unlock_at:
        return {
            "exists": True,
            "status": "available",
            "unlock_at": secret.unlock_at,
            "expires_at": secret.expires_at,
        }

    return {
        "exists": True,
        "status": "pending",
        "unlock_at": secret.unlock_at,
        "expires_at": secret.expires_at,
    }


def hard_delete_retrieved_secrets(db: Session) -> int:
    """
    Hard delete all secrets that have been retrieved.

    Returns the count of deleted rows.
    """
    result = db.query(Secret).filter(Secret.is_deleted == True).delete()  # noqa: E712
    db.commit()
    return result


def delete_expired_secrets(db: Session) -> int:
    """
    Mark expired secrets as deleted.

    Secrets with expires_at < now and retrieved_at IS NULL are marked as deleted.
    Returns the count of marked rows.
    """
    now = datetime.now(UTC).replace(tzinfo=None)

    result = (
        db.query(Secret)
        .filter(
            Secret.expires_at != None,  # noqa: E711
            Secret.expires_at < now,
            Secret.retrieved_at == None,  # noqa: E711
            Secret.is_deleted == False,  # noqa: E712
        )
        .update({"is_deleted": True})
    )
    db.commit()
    return result
