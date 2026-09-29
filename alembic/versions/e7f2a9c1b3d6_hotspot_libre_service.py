"""Paiement HotSpot en libre-service : token public routeur, ventes anonymes, table hotspot_purchases

Revision ID: e7f2a9c1b3d6
Revises: c4d8e1f2a3b5
Create Date: 2026-09-29 15:00:00

"""
import secrets
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e7f2a9c1b3d6'
down_revision: Union[str, Sequence[str], None] = 'c4d8e1f2a3b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('routers', sa.Column('public_token', sa.String(), nullable=True))
    op.create_unique_constraint('uq_routers_public_token', 'routers', ['public_token'])
    op.create_index('ix_routers_public_token', 'routers', ['public_token'])

    # Backfill : chaque routeur existant reçoit un token, sinon la page hotspot ne peut pas
    # être générée pour lui tant qu'il n'est pas re-sauvegardé.
    connection = op.get_bind()
    router_ids = [row[0] for row in connection.execute(sa.text('SELECT id FROM routers')).fetchall()]
    for router_id in router_ids:
        connection.execute(
            sa.text('UPDATE routers SET public_token = :token WHERE id = :id'),
            {"token": secrets.token_urlsafe(16), "id": router_id},
        )

    op.alter_column('sales', 'vendu_par', existing_type=sa.Integer(), nullable=True)
    op.add_column('sales', sa.Column('acheteur_telephone', sa.String(), nullable=True))

    op.create_table(
        'hotspot_purchases',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('router_id', sa.Integer(), sa.ForeignKey('routers.id'), nullable=False),
        sa.Column('batch_id', sa.Integer(), sa.ForeignKey('voucher_batches.id'), nullable=False),
        sa.Column('telephone', sa.String(), nullable=False),
        sa.Column('montant', sa.Float(), nullable=False),
        sa.Column('methode', sa.String(), nullable=False),
        sa.Column('statut', sa.String(), nullable=True, server_default='en_attente'),
        sa.Column('identifier', sa.String(), nullable=False, unique=True),
        sa.Column('voucher_id', sa.Integer(), sa.ForeignKey('vouchers.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('hotspot_purchases')
    op.drop_column('sales', 'acheteur_telephone')
    op.alter_column('sales', 'vendu_par', existing_type=sa.Integer(), nullable=False)
    op.drop_index('ix_routers_public_token', table_name='routers')
    op.drop_constraint('uq_routers_public_token', 'routers', type_='unique')
    op.drop_column('routers', 'public_token')