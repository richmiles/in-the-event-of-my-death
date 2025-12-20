import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Secret(Base):
    __tablename__ = "secrets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    edit_token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    decrypt_token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)

    # Encrypted payload
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    iv: Mapped[bytes] = mapped_column(LargeBinary(12), nullable=False)
    auth_tag: Mapped[bytes] = mapped_column(LargeBinary(16), nullable=False)

    # Timing
    unlock_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False
    )
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)

    # Metadata
    ciphertext_size: Mapped[int] = mapped_column(Integer, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
