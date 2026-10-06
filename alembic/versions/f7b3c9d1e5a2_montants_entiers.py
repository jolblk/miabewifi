"""Montants en FCFA stockés en nombres entiers (au lieu de nombres à virgule)

Le FCFA n'a pas de centimes. Les nombres à virgule (Float) créent de petites erreurs
d'arrondi (ex. 0,1 + 0,2 = 0,30000000000000004) qui finissent par fausser les soldes et
les rapprochements comptables. Les entiers sont exacts.

Les valeurs existantes sont arrondies à l'unité la plus proche. Le nombre de valeurs qui
n'étaient pas déjà entières est affiché dans les journaux du serveur au démarrage.

Revision ID: f7b3c9d1e5a2
Revises: e1f4a7b2c8d6
Create Date: 2026-10-05 18:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f7b3c9d1e5a2'
down_revision: Union[str, Sequence[str], None] = 'e1f4a7b2c8d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MONEY_COLUMNS = [
    ("users", "solde"),
    ("transactions", "montant"),
    ("voucher_batches", "prix_unitaire"),
    ("sales", "montant"),
    ("sales", "frais"),
    ("hotspot_purchases", "montant"),
]


def upgrade() -> None:
    bind = op.get_bind()
    for table, column in MONEY_COLUMNS:
        not_whole = bind.execute(sa.text(
            f"SELECT COUNT(*) FROM {table} WHERE {column} IS NOT NULL AND {column} <> ROUND({column})"
        )).scalar()
        if not_whole:
            print(f"[migration montants] {table}.{column} : {not_whole} valeur(s) non entière(s) arrondie(s) à l'unité.")
        op.alter_column(
            table, column,
            existing_type=sa.Float(),
            type_=sa.Integer(),
            postgresql_using=f"ROUND({column})::integer",
        )


def downgrade() -> None:
    for table, column in MONEY_COLUMNS:
        op.alter_column(table, column, existing_type=sa.Integer(), type_=sa.Float())