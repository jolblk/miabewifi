"""add router setup_mode

Revision ID: a1f3c7d9e2b4
Revises: 540be26919ed
Create Date: 2026-09-28 12:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1f3c7d9e2b4'
down_revision: Union[str, Sequence[str], None] = '540be26919ed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Les routeurs déjà créés sont considérés "en service" : c'est le mode le plus prudent.
    op.add_column(
        'routers',
        sa.Column('setup_mode', sa.String(), nullable=False, server_default='existing'),
    )


def downgrade() -> None:
    op.drop_column('routers', 'setup_mode')