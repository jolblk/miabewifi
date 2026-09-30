"""Tests du rattrapage des paiements de tickets (webhook PayGate manquant).

Base SQLite en mémoire : ce test ne touche jamais à la vraie base.
Lancer avec :  python -m pytest tests/test_reconcile.py
"""
import asyncio
import os
from datetime import datetime, timedelta

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("CRYPT_KEY", "0" * 43 + "=")
os.environ.setdefault("SERVER_PUBLIC_KEY", "test")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models, reconcile
from app.database import Base

NOW = datetime(2026, 9, 30, 12, 0, 0)


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    owner = models.User(email="o@test.com", hashed_password="x", nom="Owner", solde=0.0)
    session.add(owner)
    session.flush()
    router = models.Router(owner_id=owner.id, nom="R1")
    session.add(router)
    session.flush()
    batch = models.VoucherBatch(router_id=router.id, owner_id=owner.id, profile_name="Ticket-1h",
                                prix_unitaire=200, quantite=5)
    session.add(batch)
    session.flush()
    session.add_all([models.Voucher(batch_id=batch.id, code=f"CODE{i}", statut="AVAILABLE") for i in range(5)])
    session.commit()
    reconcile._last_checked.clear()
    reconcile._last_checked_recharges.clear()
    yield session
    session.close()


def _purchase(db, identifier, age, statut="en_attente"):
    batch = db.query(models.VoucherBatch).first()
    p = models.HotspotPurchase(router_id=batch.router_id, batch_id=batch.id, telephone="90000000",
                               montant=200, methode="TMONEY", statut=statut, identifier=identifier,
                               created_at=NOW - age)
    db.add(p)
    db.commit()
    return p


def _run(db, succeeded):
    """Lance le rattrapage avec un PayGate simulé : succeeded(identifier) -> bool."""
    async def fake(identifier):
        return succeeded(identifier)
    reconcile._paygate_payment_succeeded = fake
    return asyncio.run(reconcile.reconcile_pending_purchases(db, now=NOW))


def test_paid_purchase_gets_ticket_and_owner_credit(db):
    p = _purchase(db, "a", timedelta(minutes=2))
    assert _run(db, lambda i: True) == 1
    db.refresh(p)
    assert p.statut == "confirme" and p.voucher_id is not None
    assert db.query(models.User).first().solde == 198.0  # 200 - 1 % de frais
    assert db.query(models.Sale).count() == 1


def test_unpaid_purchase_stays_pending(db):
    p = _purchase(db, "a", timedelta(minutes=2))
    assert _run(db, lambda i: False) == 0
    db.refresh(p)
    assert p.statut == "en_attente" and p.voucher_id is None
    assert db.query(models.User).first().solde == 0.0


def test_too_recent_purchase_is_left_to_the_webhook(db):
    p = _purchase(db, "a", timedelta(seconds=5))
    assert _run(db, lambda i: True) == 0
    db.refresh(p)
    assert p.statut == "en_attente"


def test_too_old_purchase_is_abandoned(db):
    p = _purchase(db, "a", timedelta(hours=7))
    assert _run(db, lambda i: True) == 0
    db.refresh(p)
    assert p.statut == "en_attente"


def test_already_confirmed_purchase_is_not_processed_twice(db):
    _purchase(db, "a", timedelta(minutes=2))
    assert _run(db, lambda i: True) == 1
    assert _run(db, lambda i: True) == 0
    assert db.query(models.Sale).count() == 1
    assert db.query(models.User).first().solde == 198.0


def test_old_pending_purchase_is_rechecked_only_every_10_minutes(db):
    _purchase(db, "a", timedelta(minutes=30))
    calls = []
    def paygate(i):
        calls.append(i)
        return False
    _run(db, paygate)
    _run(db, paygate)            # 2e passage immédiat : ignoré
    assert len(calls) == 1
    reconcile._last_checked[db.query(models.HotspotPurchase).first().id] = NOW - timedelta(minutes=11)
    _run(db, paygate)            # 11 min plus tard : revérifié
    assert len(calls) == 2


def test_paygate_error_on_one_purchase_does_not_block_the_others(db):
    _purchase(db, "boom", timedelta(minutes=3))
    good = _purchase(db, "ok", timedelta(minutes=2))
    def paygate(i):
        if i == "boom":
            raise RuntimeError("PayGate injoignable")
        return True
    assert _run(db, paygate) == 1
    db.refresh(good)
    assert good.statut == "confirme"


def test_out_of_stock_triggers_refund_flow_not_a_ticket(db):
    db.query(models.Voucher).update({"statut": "USED"})
    db.commit()
    p = _purchase(db, "a", timedelta(minutes=2))
    import app.routers.wallet as wallet
    class FakeClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, *a, **k): return None
    real = wallet.httpx.AsyncClient
    wallet.httpx.AsyncClient = lambda *a, **k: FakeClient()
    try:
        _run(db, lambda i: True)
    finally:
        wallet.httpx.AsyncClient = real
    db.refresh(p)
    assert p.statut == "rembourse" and p.voucher_id is None
    assert db.query(models.User).first().solde == 0.0



# ---- Recharges du portefeuille -------------------------------------------

def _recharge(db, identifier, age, statut="en_attente", type_="recharge", montant=1000.0):
    user = db.query(models.User).first()
    t = models.Transaction(user_id=user.id, montant=montant, methode="TMONEY", statut=statut,
                           identifier=identifier, type=type_, created_at=NOW - age)
    db.add(t)
    db.commit()
    return t


def _run_recharges(db, succeeded):
    async def fake(identifier):
        return succeeded(identifier)
    reconcile._paygate_payment_succeeded = fake
    return asyncio.run(reconcile.reconcile_pending_recharges(db, now=NOW))


def test_paid_recharge_credits_wallet_once(db):
    t = _recharge(db, "r1", timedelta(minutes=2))
    assert _run_recharges(db, lambda i: True) == 1
    db.refresh(t)
    assert t.statut == "confirme"
    assert db.query(models.User).first().solde == 1000.0
    assert _run_recharges(db, lambda i: True) == 0      # 2e passage : pas de double crédit
    assert db.query(models.User).first().solde == 1000.0


def test_unpaid_recharge_is_not_credited(db):
    t = _recharge(db, "r1", timedelta(minutes=2))
    assert _run_recharges(db, lambda i: False) == 0
    db.refresh(t)
    assert t.statut == "en_attente"
    assert db.query(models.User).first().solde == 0.0


def test_withdrawals_and_other_transactions_are_never_touched(db):
    _recharge(db, "w1", timedelta(minutes=2), type_="retrait")
    _recharge(db, "v1", timedelta(minutes=2), type_="vente")
    calls = []
    def paygate(i):
        calls.append(i)
        return True
    assert _run_recharges(db, paygate) == 0
    assert calls == []
    assert db.query(models.User).first().solde == 0.0


def test_recharge_too_recent_or_too_old_is_ignored(db):
    _recharge(db, "new", timedelta(seconds=5))
    _recharge(db, "old", timedelta(hours=7))
    assert _run_recharges(db, lambda i: True) == 0
    assert db.query(models.User).first().solde == 0.0


def test_webhook_and_rattrapage_credit_only_once(db):
    """Le webhook et le rattrapage utilisent la même fonction : le 2e appel ne crédite pas."""
    from app.routers.wallet import _confirm_recharge
    t = _recharge(db, "r1", timedelta(minutes=2))
    assert _confirm_recharge(db, t) is True
    assert _confirm_recharge(db, t) is False
    assert db.query(models.User).first().solde == 1000.0


def test_paygate_error_on_one_recharge_does_not_block_the_others(db):
    _recharge(db, "boom", timedelta(minutes=3))
    good = _recharge(db, "ok", timedelta(minutes=2), montant=500.0)
    def paygate(i):
        if i == "boom":
            raise RuntimeError("PayGate injoignable")
        return True
    assert _run_recharges(db, paygate) == 1
    db.refresh(good)
    assert good.statut == "confirme"
    assert db.query(models.User).first().solde == 500.0