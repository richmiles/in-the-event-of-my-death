"""Add expires_at column to secrets table

Revision ID: 0002
Revises: 0001
Create Date: 2025-01-21

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add expires_at column to secrets table
    op.add_column("secrets", sa.Column("expires_at", sa.DateTime, nullable=True))


def downgrade() -> None:
    # Remove expires_at column from secrets table
    op.drop_column("secrets", "expires_at")
