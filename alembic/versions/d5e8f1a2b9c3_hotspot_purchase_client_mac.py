"""Adresse MAC de l'appareil qui a payé un ticket (colonne hotspot_purchases.client_mac)

Revision ID: d5e8f1a2b9c3
Revises: b6c2d9e4f1a7
Create Date: 2026-10-05 12:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd5e8f1a2b9c3'
down_revision: Union[str, Sequence[str], None] = 'b6c2d9e4f1a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('hotspot_purchases', sa.Column('client_mac', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('hotspot_purchases', 'client_mac')