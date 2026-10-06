"""Page HotSpot : slogan, téléphone de contact et photo de fond par routeur

Revision ID: a3c8e6f2d4b1
Revises: f7b3c9d1e5a2
Create Date: 2026-10-06 10:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a3c8e6f2d4b1'
down_revision: Union[str, Sequence[str], None] = 'f7b3c9d1e5a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('routers', sa.Column('brand_slogan', sa.String(), nullable=True))
    op.add_column('routers', sa.Column('brand_phone', sa.String(), nullable=True))
    op.add_column('routers', sa.Column('brand_background', sa.LargeBinary(), nullable=True))
    op.add_column('routers', sa.Column('brand_background_version', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('routers', 'brand_background_version')
    op.drop_column('routers', 'brand_background')
    op.drop_column('routers', 'brand_phone')
    op.drop_column('routers', 'brand_slogan')