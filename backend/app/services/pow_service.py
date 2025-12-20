import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.models.challenge import Challenge


def generate_challenge(db: Session, payload_hash: str, ciphertext_size: int) -> Challenge:
    """Generate a new proof-of-work challenge."""
    nonce = secrets.token_hex(32)  # 64 hex characters

    # Dynamic difficulty based on ciphertext size
    # Base difficulty + 1 per 100KB, max +4
    size_factor = min(ciphertext_size // 100_000, 4)
    difficulty = settings.pow_base_difficulty + size_factor

    expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(
        seconds=settings.pow_challenge_ttl_seconds
    )

    challenge = Challenge(
        nonce=nonce,
        difficulty=difficulty,
        payload_hash=payload_hash,
        expires_at=expires_at,
    )

    db.add(challenge)
    db.commit()
    db.refresh(challenge)

    return challenge


def verify_pow(db: Session, challenge_id: str, nonce: str, counter: int, payload_hash: str) -> bool:
    """
    Verify a proof-of-work solution.

    Returns True if valid, raises ValueError with specific message if invalid.
    """
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()

    if not challenge:
        raise ValueError("Challenge not found")

    if challenge.is_used:
        raise ValueError("Challenge already used")

    if datetime.now(UTC).replace(tzinfo=None) > challenge.expires_at:
        raise ValueError("Challenge expired")

    if challenge.nonce != nonce:
        raise ValueError("Nonce mismatch")

    if challenge.payload_hash != payload_hash:
        raise ValueError("Payload hash mismatch")

    # Reconstruct and verify hash
    # Format: nonce || counter (16 hex chars, zero-padded) || payload_hash
    preimage = f"{nonce}{counter:016x}{payload_hash}"
    hash_bytes = hashlib.sha256(preimage.encode()).digest()
    hash_int = int.from_bytes(hash_bytes, "big")

    # Check difficulty (number of leading zero bits)
    target = 2 ** (256 - challenge.difficulty)
    if hash_int >= target:
        raise ValueError("Insufficient proof of work")

    # Mark challenge as used
    challenge.is_used = True
    db.commit()

    return True


def cleanup_expired_challenges(db: Session) -> int:
    """Delete expired challenges. Returns count of deleted rows."""
    result = (
        db.query(Challenge)
        .filter(Challenge.expires_at < datetime.now(UTC).replace(tzinfo=None))
        .delete()
    )
    db.commit()
    return result
