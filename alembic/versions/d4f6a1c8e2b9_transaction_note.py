"""Note libre sur une opération (colonne transactions.note) : motif des abonnements offerts
et des corrections de solde faites par un administrateur

Revision ID: d4f6a1c8e2b9
Revises: c2e5a8b1d3f7
Create Date: 2026-10-07 12:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4f6a1c8e2b9'
down_revision: Union[str, Sequence[str], None] = 'c2e5a8b1d3f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('transactions', sa.Column('note', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('transactions', 'note')
