"""add_telegram_connect_token_hash

Revision ID: 20260811_05
Revises: 20260325_04
Create Date: 2026-08-11

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260811_05"
down_revision: str | None = "20260325_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add Telegram connect token hash column to users table
    op.add_column("users", sa.Column("telegram_connect_token_hash", sa.String(), nullable=True))


def downgrade() -> None:
    # Drop Telegram connect token hash column
    op.drop_column("users", "telegram_connect_token_hash")
