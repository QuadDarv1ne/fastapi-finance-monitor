"""Alembic revision template."""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

${message if message else ''}

revision = '${rev_id}'
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass
