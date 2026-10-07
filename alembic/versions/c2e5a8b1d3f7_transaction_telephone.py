"""Numéro mobile money des recharges et retraits (colonne transactions.telephone)

Revision ID: c2e5a8b1d3f7
Revises: b9d2f4e6a8c1
Create Date: 2026-10-07 10:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c2e5a8b1d3f7'
down_revision: Union[str, Sequence[str], None] = 'b9d2f4e6a8c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('transactions', sa.Column('telephone', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('transactions', 'telephone')
