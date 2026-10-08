"""Sessions révocables (users.token_version) et index sur le numéro des achats HotSpot

Revision ID: a7c3e9f1b2d4
Revises: d4f6a1c8e2b9
Create Date: 2026-10-08 12:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a7c3e9f1b2d4'
down_revision: Union[str, Sequence[str], None] = 'd4f6a1c8e2b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 0 pour tous les comptes existants : les connexions en cours restent valables.
    op.add_column('users', sa.Column('token_version', sa.Integer(), nullable=False, server_default='0'))
    # Recherche rapide des demandes récentes vers un même numéro (limite anti-harcèlement).
    op.create_index('ix_hotspot_purchases_telephone', 'hotspot_purchases', ['telephone'])


def downgrade() -> None:
    op.drop_index('ix_hotspot_purchases_telephone', table_name='hotspot_purchases')
    op.drop_column('users', 'token_version')
