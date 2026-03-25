"""add_2fa_fields_to_users

Revision ID: 20260325_04
Revises: 20260325_03
Create Date: 2026-03-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260325_04'
down_revision: Union[str, None] = '20260325_03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 2FA columns to users table
    op.add_column('users', sa.Column('is_2fa_enabled', sa.Boolean(), nullable=True, default=False))
    op.add_column('users', sa.Column('totp_secret', sa.String(), nullable=True))
    
    # Set default value for existing rows
    op.execute("UPDATE users SET is_2fa_enabled = FALSE WHERE is_2fa_enabled IS NULL")


def downgrade() -> None:
    # Drop 2FA columns
    op.drop_column('users', 'totp_secret')
    op.drop_column('users', 'is_2fa_enabled')
