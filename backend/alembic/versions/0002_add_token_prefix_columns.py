"""Add token prefix columns for O(1) lookup

Revision ID: 0002
Revises: 0001
Create Date: 2025-12-31

Adds edit_token_prefix and decrypt_token_prefix columns to secrets table.
These indexed columns store the first 16 hex chars of each token, enabling
O(1) database lookup before Argon2 verification (instead of O(N) scans).

For existing secrets (if any), we generate random prefixes since we can't
recover the original tokens. These secrets will be orphaned but will
expire naturally. This is acceptable for a new service with minimal data.
"""

import secrets
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add columns as nullable first
    op.add_column(
        "secrets",
        sa.Column("edit_token_prefix", sa.String(16), nullable=True),
    )
    op.add_column(
        "secrets",
        sa.Column("decrypt_token_prefix", sa.String(16), nullable=True),
    )

    # Backfill existing rows with random prefixes
    # These secrets become orphaned but will expire naturally
    connection = op.get_bind()
    secrets_table = sa.table(
        "secrets",
        sa.column("id", sa.String),
        sa.column("edit_token_prefix", sa.String),
        sa.column("decrypt_token_prefix", sa.String),
    )

    # Get all existing secrets
    result = connection.execute(sa.select(secrets_table.c.id))
    for row in result:
        connection.execute(
            secrets_table.update()
            .where(secrets_table.c.id == row.id)
            .values(
                edit_token_prefix=secrets.token_hex(8),  # 16 hex chars
                decrypt_token_prefix=secrets.token_hex(8),
            )
        )

    # Now make columns non-nullable
    with op.batch_alter_table("secrets") as batch_op:
        batch_op.alter_column("edit_token_prefix", nullable=False)
        batch_op.alter_column("decrypt_token_prefix", nullable=False)

    # Create indexes for fast prefix lookup
    op.create_index("ix_secrets_edit_token_prefix", "secrets", ["edit_token_prefix"])
    op.create_index("ix_secrets_decrypt_token_prefix", "secrets", ["decrypt_token_prefix"])


def downgrade() -> None:
    op.drop_index("ix_secrets_decrypt_token_prefix", table_name="secrets")
    op.drop_index("ix_secrets_edit_token_prefix", table_name="secrets")
    op.drop_column("secrets", "decrypt_token_prefix")
    op.drop_column("secrets", "edit_token_prefix")
