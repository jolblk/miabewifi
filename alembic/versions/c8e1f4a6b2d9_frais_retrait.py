"""Frais de retrait réglables : table platform_settings et colonne transactions.frais

Revision ID: c8e1f4a6b2d9
Revises: a7c3e9f1b2d4
Create Date: 2026-10-10 03:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c8e1f4a6b2d9'
down_revision: Union[str, Sequence[str], None] = 'a7c3e9f1b2d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'platform_settings',
        sa.Column('key', sa.String(), primary_key=True),
        sa.Column('value', sa.String(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('updated_by', sa.String(), nullable=True),
    )
    # 2 % au départ, modifiable ensuite dans l'administration.
    op.execute(
        "INSERT INTO platform_settings (key, value, updated_at) "
        "VALUES ('frais_retrait_pourcent', '2', CURRENT_TIMESTAMP)"
    )
    op.add_column('transactions', sa.Column('frais', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('transactions', 'frais')
    op.drop_table('platform_settings')
