"""Essai gratuit limité à une fois par compte (colonne users.trial_used)

Revision ID: e1f4a7b2c8d6
Revises: d5e8f1a2b9c3
Create Date: 2026-10-05 14:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e1f4a7b2c8d6'
down_revision: Union[str, Sequence[str], None] = 'd5e8f1a2b9c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('trial_used', sa.Boolean(), nullable=False, server_default=sa.false()))
    # Les comptes qui ont déjà un routeur ont déjà profité de leur essai.
    op.execute("UPDATE users SET trial_used = TRUE WHERE id IN (SELECT owner_id FROM routers)")


def downgrade() -> None:
    op.drop_column('users', 'trial_used')