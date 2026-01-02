"""Add capability_tokens table

Revision ID: 0003
Revises: 0002
Create Date: 2025-01-02

Adds capability_tokens table for premium feature access tokens.
Tokens are bearer instruments that bypass PoW and enable larger file uploads.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "capability_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("token_prefix", sa.String(16), nullable=False),
        sa.Column("token_hash", sa.String(128), unique=True, nullable=False),
        sa.Column("tier", sa.String(20), nullable=False),
        sa.Column("max_file_size_bytes", sa.Integer, nullable=False),
        sa.Column("max_expiry_days", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("consumed_at", sa.DateTime, nullable=True),
        sa.Column(
            "consumed_by_secret_id",
            sa.String(36),
            sa.ForeignKey("secrets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("payment_provider", sa.String(50), nullable=True),
        sa.Column("payment_reference", sa.String(255), nullable=True),
    )

    # Indexes
    op.create_index("ix_capability_tokens_token_prefix", "capability_tokens", ["token_prefix"])
    op.create_index("ix_capability_tokens_expires_at", "capability_tokens", ["expires_at"])
    op.create_index(
        "ix_capability_tokens_consumed_by_secret_id",
        "capability_tokens",
        ["consumed_by_secret_id"],
    )
    op.create_index(
        "ix_capability_tokens_payment_reference",
        "capability_tokens",
        ["payment_reference"],
    )


def downgrade() -> None:
    op.drop_index("ix_capability_tokens_payment_reference", table_name="capability_tokens")
    op.drop_index("ix_capability_tokens_consumed_by_secret_id", table_name="capability_tokens")
    op.drop_index("ix_capability_tokens_expires_at", table_name="capability_tokens")
    op.drop_index("ix_capability_tokens_token_prefix", table_name="capability_tokens")
    op.drop_table("capability_tokens")
