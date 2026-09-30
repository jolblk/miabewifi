"""Tests de la règle d'accès d'un routeur : essai de 3 jours OU abonnement actif.

Lancer avec :  python -m pytest tests/test_router_access.py
"""
from datetime import datetime, timedelta
from types import SimpleNamespace

from app.wireguard import is_router_active


def _router(trial=None, sub=None):
    return SimpleNamespace(trial_expires_at=trial, subscription_expires_at=sub)


NOW = datetime.utcnow()
FUTURE = NOW + timedelta(days=2)
PAST = NOW - timedelta(days=2)


def test_active_during_trial():
    assert is_router_active(_router(trial=FUTURE)) is True


def test_inactive_after_trial_without_subscription():
    assert is_router_active(_router(trial=PAST)) is False


def test_active_with_subscription_after_trial_ended():
    assert is_router_active(_router(trial=PAST, sub=FUTURE)) is True


def test_inactive_when_both_expired():
    assert is_router_active(_router(trial=PAST, sub=PAST)) is False


def test_inactive_when_no_dates_at_all():
    assert is_router_active(_router()) is False


def test_active_with_subscription_and_no_trial():
    assert is_router_active(_router(sub=FUTURE)) is True
