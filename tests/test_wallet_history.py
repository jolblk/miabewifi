"""Tests de la présentation du portefeuille (app/wallet_history.py) : numéros masqués,
libellés, bilan du mois. Lancer avec :  pytest tests/test_wallet_history.py
"""
from datetime import datetime
from types import SimpleNamespace

import pytest

from app import wallet_history as wh


def _tx(**kw):
    base = dict(id=1, type="recharge", statut="confirme", montant=1000, methode="FLOOZ", created_at=datetime(2026, 10, 1), telephone=None)
    base.update(kw)
    return SimpleNamespace(**base)


def test_numero_masque():
    assert wh.mask_phone("90123412") == "90 •• •• 12"
    assert wh.mask_phone("+228 99 88 77 47") == "99 •• •• 47"
    assert wh.mask_phone(None) == ""


def test_vente_en_ligne_detaillee():
    row = wh.describe(
        _tx(type="vente", montant=297, methode="TMONEY"),
        sale=SimpleNamespace(frais=3, acheteur_telephone="99887747"),
        forfait="24 heures",
    )
    assert row["titre"] == "Vente en ligne · 24 heures"
    assert row["detail"] == "T-Money 99 •• •• 47 · frais 3 F"
    assert row["montant_signe"] == 297 and row["frais"] == 3


def test_retrait_en_verification():
    row = wh.describe(_tx(type="retrait", statut="a_verifier", montant=5000, telephone="90123488"))
    assert row["titre"] == "Retrait vers Flooz 90 •• •• 88"
    assert row["detail"] == "En vérification"
    assert row["montant_signe"] == -5000


def test_abonnement_avec_nom_du_routeur():
    row = wh.describe(_tx(type="debit", methode="PACK", montant=6000), router_name="Cyber Chez Ama")
    assert row["titre"] == "Abonnement · Cyber Chez Ama" and row["montant_signe"] == -6000


def test_bilan_du_mois():
    summary = wh.month_summary([
        ("vente", "confirme", 297, 3),
        ("vente", "confirme", 99, 1),
        ("recharge", "confirme", 5000, None),
        ("recharge", "en_attente", 500, None),   # pas encore payée : ignorée
        ("debit", "confirme", 6000, None),
        ("retrait", "a_verifier", 5000, None),   # montant réservé : compté
        ("retrait", "echoue", 2000, None),       # rendu au solde : ignoré
    ])
    assert summary == {"ventes": 400, "frais": 4, "recharges": 5000, "abonnements": 6000, "retraits": 5000, "net": -5604}


def test_bornes_du_mois():
    assert wh.month_bounds("2026-12") == (datetime(2026, 12, 1), datetime(2027, 1, 1))
    assert wh.month_bounds(None, now=datetime(2026, 10, 7)) == (datetime(2026, 10, 1), datetime(2026, 11, 1))
    with pytest.raises(ValueError):
        wh.month_bounds("2026-13")
