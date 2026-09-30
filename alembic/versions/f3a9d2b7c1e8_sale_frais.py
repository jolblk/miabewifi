"""Frais prélevés sur les ventes en libre-service (colonne sales.frais)

Revision ID: f3a9d2b7c1e8
Revises: e7f2a9c1b3d6
Create Date: 2026-09-30 10:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f3a9d2b7c1e8'
down_revision: Union[str, Sequence[str], None] = 'e7f2a9c1b3d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('sales', sa.Column('frais', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('sales', 'frais')
