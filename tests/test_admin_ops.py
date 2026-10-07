"""Tests des règles d'administration (app/admin_ops.py).
Lancer avec :  pytest tests/test_admin_ops.py
"""
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from app.admin_ops import check_adjustment, extended_expiry, subscription_kind

NOW = datetime(2026, 10, 7, 12, 0)


def _r(sub=None, trial=None):
    return SimpleNamespace(subscription_expires_at=sub, trial_expires_at=trial)


def test_type_d_abonnement():
    assert subscription_kind(_r(sub=NOW + timedelta(days=3)), "OFFERT", NOW) == "offert"
    assert subscription_kind(_r(sub=NOW + timedelta(days=3)), "PACK", NOW) == "abonnement"
    assert subscription_kind(_r(trial=NOW + timedelta(days=1)), None, NOW) == "essai"
    assert subscription_kind(_r(sub=NOW - timedelta(days=1)), "PACK", NOW) == "expire"
    assert subscription_kind(_r(), None, NOW) == "aucun"


def test_jours_offerts_s_ajoutent_a_l_abonnement_en_cours():
    assert extended_expiry(NOW + timedelta(days=10), NOW, 30) == NOW + timedelta(days=40)
    assert extended_expiry(NOW - timedelta(days=10), NOW, 30) == NOW + timedelta(days=30)
    assert extended_expiry(None, NOW, 7) == NOW + timedelta(days=7)
    with pytest.raises(ValueError):
        extended_expiry(None, NOW, 0)


def test_correction_de_solde():
    check_adjustment(1000, -1000, "Doublon")
    for solde, montant, motif in [(1000, 0, "x" * 5), (1000, 500, ""), (1000, -1500, "Doublon")]:
        with pytest.raises(ValueError):
            check_adjustment(solde, montant, motif)


# ---- création du compte administrateur ---------------------------------------------
def test_creation_puis_mise_a_jour_du_compte_admin(monkeypatch):
    import app.create_admin as ca

    class FakeQuery:
        def __init__(self, db):
            self.db = db

        def filter(self, *a):
            return self

        def first(self):
            return self.db.users[0] if self.db.users else None

    class FakeDB:
        def __init__(self):
            self.users, self.commits = [], 0

        def query(self, model):
            return FakeQuery(self)

        def add(self, obj):
            self.users.append(obj)

        def commit(self):
            self.commits += 1

    class FakeUser:
        email = None

        def __init__(self, **kw):
            self.__dict__.update(kw)

    monkeypatch.setattr(ca, "hash_password", lambda p: f"hash:{p}")
    monkeypatch.setattr(ca.models, "User", FakeUser)
    db = FakeDB()
    assert ca.create_or_update_admin(db, " admin ", "motdepasse1") == "créé"
    assert db.users[0].email == "admin" and db.users[0].role == "admin" and db.users[0].hashed_password == "hash:motdepasse1"
    assert ca.create_or_update_admin(db, "admin", "autre-mdp-2") == "mis à jour"
    assert db.users[0].hashed_password == "hash:autre-mdp-2" and len(db.users) == 1
    with pytest.raises(ValueError):
        ca.create_or_update_admin(db, "admin", "court")
