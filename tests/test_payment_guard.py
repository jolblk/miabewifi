"""Tests de la limite de demandes de paiement par numéro (app/payment_guard.py).
Lancer avec :  python -m pytest tests/test_payment_guard.py
"""
from datetime import datetime, timedelta

from app.payment_guard import phone_request_allowed

NOW = datetime(2026, 10, 8, 12, 0, 0)


def _ago(**kwargs):
    return NOW - timedelta(**kwargs)


def test_premiere_demande_autorisee():
    assert phone_request_allowed([], NOW)


def test_deux_demandes_recentes_encore_autorisees():
    assert phone_request_allowed([_ago(minutes=1), _ago(minutes=3)], NOW)


def test_trois_demandes_en_dix_minutes_bloquent():
    assert not phone_request_allowed([_ago(minutes=1), _ago(minutes=4), _ago(minutes=9)], NOW)


def test_les_demandes_anciennes_ne_comptent_plus_pour_les_dix_minutes():
    assert phone_request_allowed([_ago(minutes=11), _ago(minutes=20), _ago(minutes=1)], NOW)


def test_six_demandes_dans_l_heure_bloquent():
    times = [_ago(minutes=m) for m in (12, 20, 30, 40, 50, 55)]
    assert not phone_request_allowed(times, NOW)


def test_au_dela_d_une_heure_tout_est_oublie():
    times = [_ago(minutes=m) for m in (61, 70, 80, 90, 100, 110, 120)]
    assert phone_request_allowed(times, NOW)
