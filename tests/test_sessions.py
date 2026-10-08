"""Tests des connexions révocables (app/security.py).
Lancer avec :  python -m pytest tests/test_sessions.py
"""
from datetime import datetime

from app import security


def _exp_hours(token):
    payload = security.decode_access_token(token)
    return (datetime.utcfromtimestamp(payload["exp"]) - datetime.utcnow()).total_seconds() / 3600


def test_le_jeton_porte_le_numero_de_version():
    payload = security.decode_access_token(security.create_access_token(7, token_version=3))
    assert payload["sub"] == "7" and payload["ver"] == 3


def test_duree_selon_rester_connecte():
    assert 24 * 7 - 1 < _exp_hours(security.create_access_token(1, remember=True)) <= 24 * 7
    assert 11 < _exp_hours(security.create_access_token(1, remember=False)) <= 12


def test_jeton_perime_apres_changement_de_mot_de_passe():
    payload = security.decode_access_token(security.create_access_token(1, token_version=0))
    assert security.token_is_current(payload, 0)
    assert not security.token_is_current(payload, 1)


def test_anciens_jetons_sans_version_restent_valables_au_depart():
    assert security.token_is_current({"sub": "1"}, 0)
    assert security.token_is_current({"sub": "1"}, None)
    assert not security.token_is_current({"sub": "1"}, 1)


def test_un_lien_de_reinitialisation_ne_sert_pas_de_connexion():
    reset = security.create_reset_token(1)
    assert security.decode_access_token(reset) is None
    assert security.decode_reset_token(reset) is not None


def test_une_connexion_ne_sert_pas_de_lien_de_reinitialisation():
    assert security.decode_reset_token(security.create_access_token(1)) is None


def test_jeton_falsifie_refuse():
    token = security.create_access_token(1)
    assert security.decode_access_token(token[:-2] + "xx") is None
