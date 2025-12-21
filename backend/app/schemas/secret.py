import base64
import re
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, Field, field_validator

from app.config import settings


def strict_base64_decode(value: str, field_name: str) -> bytes:
    """
    Strictly validate and decode base64 string.

    Rejects strings with invalid characters, incorrect padding, or whitespace.
    """
    # Check for valid base64 characters only (no whitespace allowed)
    if not re.match(r"^[A-Za-z0-9+/]*={0,2}$", value):
        raise ValueError(f"{field_name}: Invalid base64 characters")
    # Check length is multiple of 4
    if len(value) % 4 != 0:
        raise ValueError(f"{field_name}: Invalid base64 length (must be multiple of 4)")
    try:
        return base64.b64decode(value, validate=True)
    except Exception:
        raise ValueError(f"{field_name}: Invalid base64 encoding")


class PowProof(BaseModel):
    challenge_id: str
    nonce: str = Field(..., min_length=64, max_length=64, pattern=r"^[a-f0-9]{64}$")
    counter: int = Field(..., ge=0)
    payload_hash: str = Field(..., min_length=64, max_length=64, pattern=r"^[a-f0-9]{64}$")


class SecretCreate(BaseModel):
    ciphertext: str = Field(..., description="Base64 encoded ciphertext")
    iv: str = Field(..., description="Base64 encoded 12-byte IV")
    auth_tag: str = Field(..., description="Base64 encoded 16-byte auth tag")
    unlock_at: datetime
    expires_at: datetime | None = None
    edit_token: str = Field(..., min_length=64, max_length=64, description="Hex token")
    decrypt_token: str = Field(..., min_length=64, max_length=64, description="Hex token")
    pow_proof: PowProof

    @field_validator("ciphertext")
    @classmethod
    def validate_ciphertext_base64(cls, v: str) -> str:
        decoded = strict_base64_decode(v, "ciphertext")
        if len(decoded) > settings.max_ciphertext_size:
            raise ValueError(f"Ciphertext exceeds {settings.max_ciphertext_size} bytes")
        if len(decoded) < 1:
            raise ValueError("Ciphertext cannot be empty")
        return v

    @field_validator("iv")
    @classmethod
    def validate_iv(cls, v: str) -> str:
        decoded = strict_base64_decode(v, "iv")
        if len(decoded) != 12:
            raise ValueError("IV must be exactly 12 bytes")
        return v

    @field_validator("auth_tag")
    @classmethod
    def validate_auth_tag(cls, v: str) -> str:
        decoded = strict_base64_decode(v, "auth_tag")
        if len(decoded) != 16:
            raise ValueError("Auth tag must be exactly 16 bytes")
        return v

    @field_validator("unlock_at")
    @classmethod
    def validate_unlock_at(cls, v: datetime) -> datetime:
        now = datetime.now(UTC).replace(tzinfo=None)
        min_unlock = now + timedelta(minutes=settings.min_unlock_minutes)
        max_unlock = now + timedelta(days=settings.max_unlock_days)

        # Make v timezone-naive for comparison
        v_naive = v.replace(tzinfo=None) if v.tzinfo else v

        if v_naive < min_unlock:
            raise ValueError(
                f"Unlock date must be at least {settings.min_unlock_minutes} minutes in the future"
            )
        if v_naive > max_unlock:
            raise ValueError(f"Unlock date cannot exceed {settings.max_unlock_days} days")
        return v_naive

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(cls, v: datetime | None, info) -> datetime | None:
        if v is None:
            return None

        # Make v timezone-naive for comparison
        v_naive = v.replace(tzinfo=None) if v.tzinfo else v

        # If unlock_at is already validated, check that expires_at is after it
        if "unlock_at" in info.data:
            unlock_at = info.data["unlock_at"]
            unlock_at_naive = unlock_at.replace(tzinfo=None) if unlock_at.tzinfo else unlock_at
            if v_naive <= unlock_at_naive:
                raise ValueError("expires_at must be after unlock_at")

        return v_naive


class SecretCreateResponse(BaseModel):
    secret_id: str
    unlock_at: datetime
    expires_at: datetime | None = None
    created_at: datetime


class SecretEditRequest(BaseModel):
    unlock_at: datetime

    @field_validator("unlock_at")
    @classmethod
    def validate_unlock_at(cls, v: datetime) -> datetime:
        now = datetime.now(UTC).replace(tzinfo=None)
        max_unlock = now + timedelta(days=settings.max_unlock_days)
        v_naive = v.replace(tzinfo=None) if v.tzinfo else v
        if v_naive > max_unlock:
            raise ValueError(f"Unlock date cannot exceed {settings.max_unlock_days} days")
        return v_naive


class SecretEditResponse(BaseModel):
    secret_id: str
    unlock_at: datetime
    updated_at: datetime


class SecretStatusResponse(BaseModel):
    exists: bool
    status: str  # "pending" | "available" | "retrieved"
    unlock_at: datetime | None = None
    expires_at: datetime | None = None


class SecretRetrieveResponse(BaseModel):
    status: str
    ciphertext: str | None = None
    iv: str | None = None
    auth_tag: str | None = None
    unlock_at: datetime | None = None
    retrieved_at: datetime | None = None
    message: str | None = None
