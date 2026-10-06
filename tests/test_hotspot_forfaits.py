"""Tests des prix par forfait (app/routers/hotspot_forfaits.py).
Lancer avec :  pytest tests/test_hotspot_forfaits.py
(variables d'environnement requises par app.config : DATABASE_URL, CRYPT_KEY, SERVER_PUBLIC_KEY)
"""
import pytest
from pydantic import ValidationError

from app.routers.hotspot_forfaits import ForfaitSettingIn


def test_prix_obligatoire_et_positif():
    assert ForfaitSettingIn(prix=100).prix == 100
    for bad in [0, -50]:
        with pytest.raises(ValidationError):
            ForfaitSettingIn(prix=bad)


def test_prix_entier_uniquement():
    with pytest.raises(ValidationError):
        ForfaitSettingIn(prix=100.5)


def test_options_facultatives_et_bornees():
    s = ForfaitSettingIn(prix=300, validite_jours=30, quota_mo=1024)
    assert (s.validite_jours, s.quota_mo) == (30, 1024)
    assert ForfaitSettingIn(prix=300).validite_jours is None
    with pytest.raises(ValidationError):
        ForfaitSettingIn(prix=300, validite_jours=0)
    with pytest.raises(ValidationError):
        ForfaitSettingIn(prix=300, validite_jours=400)
