"""reminders

Revision ID: 5b1e7c2d9a40
Revises: 3ad97ae20e6a
Create Date: 2026-10-24 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '5b1e7c2d9a40'
down_revision: str | None = '3ad97ae20e6a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('item', schema=None) as batch_op:
        batch_op.add_column(sa.Column('reminders', sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('item', schema=None) as batch_op:
        batch_op.drop_column('reminders')
