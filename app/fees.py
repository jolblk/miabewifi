"""Calcul des frais prélevés sur les ventes de tickets en libre-service.

Module volontairement sans dépendance (ni base de données, ni FastAPI) pour pouvoir
être testé isolément. Les montants sont en FCFA (pas de centimes) : les frais sont
arrondis à l'entier SUPÉRIEUR, pour ne jamais vendre à perte face aux frais PayGate.
"""
from decimal import Decimal, ROUND_CEILING


def compute_sale_split(montant, rate) -> tuple[int, int]:
    """Retourne (frais, net) pour une vente de `montant` FCFA avec un taux `rate`
    (ex: 0.01 pour 1 %). On a toujours frais + net == montant, et 0 <= frais <= montant."""
    m = Decimal(str(montant))
    r = Decimal(str(rate))
    if m <= 0:
        raise ValueError("Le montant doit être strictement positif.")
    if r < 0 or r >= 1:
        raise ValueError("Le taux de frais doit être compris entre 0 (inclus) et 1 (exclu).")

    frais = (m * r).to_integral_value(rounding=ROUND_CEILING)
    if frais > m:
        frais = m
    net = m - frais
    return int(frais), int(net)
