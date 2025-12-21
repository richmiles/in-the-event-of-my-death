"""Create secrets and pow_challenges tables

Revision ID: 0001
Revises:
Create Date: 2025-12-20

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create secrets table
    op.create_table(
        "secrets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("edit_token_hash", sa.String(128), unique=True, nullable=False),
        sa.Column("decrypt_token_hash", sa.String(128), unique=True, nullable=False),
        sa.Column("ciphertext", sa.LargeBinary, nullable=False),
        sa.Column("iv", sa.LargeBinary(12), nullable=False),
        sa.Column("auth_tag", sa.LargeBinary(16), nullable=False),
        sa.Column("unlock_at", sa.DateTime, nullable=False),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("retrieved_at", sa.DateTime, nullable=True),
        sa.Column("ciphertext_size", sa.Integer, nullable=False),
        sa.Column("is_deleted", sa.Boolean, default=False, nullable=False),
    )

    # Create indexes for secrets table
    op.create_index("ix_secrets_unlock_at", "secrets", ["unlock_at"])
    op.create_index("ix_secrets_expires_at", "secrets", ["expires_at"])
    op.create_index("ix_secrets_edit_token_hash", "secrets", ["edit_token_hash"])
    op.create_index("ix_secrets_decrypt_token_hash", "secrets", ["decrypt_token_hash"])

    # Create pow_challenges table
    op.create_table(
        "pow_challenges",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("nonce", sa.String(64), unique=True, nullable=False),
        sa.Column("difficulty", sa.Integer, nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("is_used", sa.Boolean, default=False, nullable=False),
    )

    # Create indexes for pow_challenges table
    op.create_index("ix_pow_challenges_nonce", "pow_challenges", ["nonce"])
    op.create_index("ix_pow_challenges_expires_at", "pow_challenges", ["expires_at"])


def downgrade() -> None:
    # Drop indexes first
    op.drop_index("ix_pow_challenges_expires_at", table_name="pow_challenges")
    op.drop_index("ix_pow_challenges_nonce", table_name="pow_challenges")
    op.drop_table("pow_challenges")

    op.drop_index("ix_secrets_expires_at", table_name="secrets")
    op.drop_index("ix_secrets_decrypt_token_hash", table_name="secrets")
    op.drop_index("ix_secrets_edit_token_hash", table_name="secrets")
    op.drop_index("ix_secrets_unlock_at", table_name="secrets")
    op.drop_table("secrets")
