"""Tests des règles d'ajout de routeur (app/router_policy.py).
Lancer avec :  python -m pytest tests/test_router_policy.py
"""
import pytest

from app.router_policy import MAX_UNPAID_ROUTERS, RouterLimitReached, decide_router_creation


def test_premier_routeur_recoit_l_essai():
    assert decide_router_creation(is_admin=False, trial_used=False, unpaid_routers=0) is True


def test_essai_une_seule_fois_par_compte():
    # Supprimer puis recréer son routeur ne redonne pas d'essai gratuit.
    assert decide_router_creation(is_admin=False, trial_used=True, unpaid_routers=0) is False


def test_limite_de_routeurs_jamais_payes():
    with pytest.raises(RouterLimitReached):
        decide_router_creation(is_admin=False, trial_used=True, unpaid_routers=MAX_UNPAID_ROUTERS)


def test_sous_la_limite_on_peut_ajouter():
    assert decide_router_creation(is_admin=False, trial_used=True, unpaid_routers=MAX_UNPAID_ROUTERS - 1) is False


def test_admin_sans_limite_mais_essai_unique():
    assert decide_router_creation(is_admin=True, trial_used=True, unpaid_routers=50) is False
    assert decide_router_creation(is_admin=True, trial_used=False, unpaid_routers=50) is True