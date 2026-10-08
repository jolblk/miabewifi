"""Tests des contrôles de saisie côté serveur (app/schemas.py).
Lancer avec :  python -m pytest tests/test_input_validation.py
"""
import pytest
from pydantic import ValidationError

from app.schemas import RechargeRequest, SaleCreate, SupportMessage, UserCreate, WithdrawRequest


def test_recharge_valide():
    r = RechargeRequest(phone_number="+22890000000", network="TMONEY", montant=5000)
    assert r.network == "TMONEY"


@pytest.mark.parametrize("phone", ["90 00 00 00", "abc", "123", "9000000000000000", ""])
def test_numero_invalide_refuse(phone):
    with pytest.raises(ValidationError):
        RechargeRequest(phone_number=phone, network="FLOOZ", montant=1000)


@pytest.mark.parametrize("network", ["flooz", "ORANGE", "", "FLOOZ; DROP"])
def test_operateur_inconnu_refuse(network):
    with pytest.raises(ValidationError):
        WithdrawRequest(phone_number="90000000", network=network, montant=1000, password="x")


@pytest.mark.parametrize("montant", [0, -500, 10_000_001])
def test_montant_hors_limites_refuse(montant):
    with pytest.raises(ValidationError):
        WithdrawRequest(phone_number="90000000", network="FLOOZ", montant=montant, password="x")


def test_vente_manuelle_jamais_negative():
    assert SaleCreate().montant is None
    assert SaleCreate(montant=0).montant == 0  # ticket offert
    with pytest.raises(ValidationError):
        SaleCreate(montant=-200)


def test_nom_et_message_limites_en_longueur():
    with pytest.raises(ValidationError):
        UserCreate(email="a@exemple.tg", password="motdepasse", nom="x" * 101)
    with pytest.raises(ValidationError):
        UserCreate(email="a@exemple.tg", password="motdepasse", nom="")
    with pytest.raises(ValidationError):
        SupportMessage(message="x" * 3001)
