"""Réglages du HotSpot choisis par le client : quota de données, vente en ligne par lot, personnalisation, format des codes

Revision ID: b6c2d9e4f1a7
Revises: f3a9d2b7c1e8
Create Date: 2026-09-30 14:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b6c2d9e4f1a7'
down_revision: Union[str, Sequence[str], None] = 'f3a9d2b7c1e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Les valeurs par défaut reproduisent le comportement d'avant : vente en ligne active,
    # codes de 8 caractères hexadécimaux sans préfixe, pas de personnalisation, pas de quota.
    op.add_column('routers', sa.Column('online_sales_enabled', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column('routers', sa.Column('brand_name', sa.String(), nullable=True))
    op.add_column('routers', sa.Column('brand_color', sa.String(), nullable=True))
    op.add_column('routers', sa.Column('brand_logo', sa.Text(), nullable=True))
    op.add_column('routers', sa.Column('code_prefix', sa.String(), nullable=True))
    op.add_column('routers', sa.Column('code_length', sa.Integer(), nullable=False, server_default='8'))
    op.add_column('routers', sa.Column('code_digits_only', sa.Boolean(), nullable=False, server_default=sa.false()))

    op.add_column('voucher_batches', sa.Column('quota_mo', sa.Integer(), nullable=True))
    op.add_column('voucher_batches', sa.Column('online_sale', sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade() -> None:
    op.drop_column('voucher_batches', 'online_sale')
    op.drop_column('voucher_batches', 'quota_mo')

    op.drop_column('routers', 'code_digits_only')
    op.drop_column('routers', 'code_length')
    op.drop_column('routers', 'code_prefix')
    op.drop_column('routers', 'brand_logo')
    op.drop_column('routers', 'brand_color')
    op.drop_column('routers', 'brand_name')
    op.drop_column('routers', 'online_sales_enabled')
