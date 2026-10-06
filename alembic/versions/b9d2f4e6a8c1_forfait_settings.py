"""Prix et options de vente par forfait et par routeur (table forfait_settings)

Revision ID: b9d2f4e6a8c1
Revises: a3c8e6f2d4b1
Create Date: 2026-10-06 14:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b9d2f4e6a8c1'
down_revision: Union[str, Sequence[str], None] = 'a3c8e6f2d4b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'forfait_settings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('router_id', sa.Integer(), sa.ForeignKey('routers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('profile_name', sa.String(), nullable=False),
        sa.Column('prix', sa.Integer(), nullable=False),
        sa.Column('validite_jours', sa.Integer(), nullable=True),
        sa.Column('quota_mo', sa.Integer(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('router_id', 'profile_name', name='uq_forfait_settings_router_profile'),
    )
    op.create_index('ix_forfait_settings_id', 'forfait_settings', ['id'])
    op.create_index('ix_forfait_settings_router_id', 'forfait_settings', ['router_id'])

    # Point de départ : pour chaque forfait déjà vendu, on reprend le prix du lot le plus récent.
    op.execute("""
        INSERT INTO forfait_settings (router_id, profile_name, prix, validite_jours, quota_mo, updated_at)
        SELECT DISTINCT ON (router_id, profile_name)
               router_id, profile_name, prix_unitaire, validite_jours, quota_mo, NOW()
        FROM voucher_batches
        WHERE router_id IS NOT NULL AND profile_name IS NOT NULL AND prix_unitaire > 0
        ORDER BY router_id, profile_name, created_at DESC
    """)


def downgrade() -> None:
    op.drop_index('ix_forfait_settings_router_id', table_name='forfait_settings')
    op.drop_index('ix_forfait_settings_id', table_name='forfait_settings')
    op.drop_table('forfait_settings')
