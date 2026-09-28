"""wifi_ssid, validité calendaire et suivi de première connexion des tickets

Revision ID: c4d8e1f2a3b5
Revises: a1f3c7d9e2b4
Create Date: 2026-09-29 09:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c4d8e1f2a3b5'
down_revision: Union[str, Sequence[str], None] = 'a1f3c7d9e2b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('routers', sa.Column('wifi_ssid', sa.String(), nullable=True))
    op.add_column('voucher_batches', sa.Column('validite_jours', sa.Integer(), nullable=True))
    op.add_column('voucher_batches', sa.Column('limit_uptime', sa.String(), nullable=True))
    op.add_column('vouchers', sa.Column('first_login_at', sa.DateTime(), nullable=True))
    op.add_column('vouchers', sa.Column('expires_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('vouchers', 'expires_at')
    op.drop_column('vouchers', 'first_login_at')
    op.drop_column('voucher_batches', 'limit_uptime')
    op.drop_column('voucher_batches', 'validite_jours')
    op.drop_column('routers', 'wifi_ssid')
