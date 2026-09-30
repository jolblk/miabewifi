# Lancer depuis la racine du projet :  python tests/verify_access_control.py
# (volontairement nommé verify_* : pytest ne le charge pas, car il remplace des modules par des faux)
"""Vérification isolée (SANS base ni dépendances) : exécute les VRAIES routes de
app/routers/hotspot.py et app/routers/hotspot_public.py avec une fausse base de données,
pour prouver que l'essai/abonnement expiré bloque ce qui doit l'être, et rien d'autre."""
import sys, types, asyncio, importlib
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

sys.path.insert(0, ".")


def stub(name, **attrs):
    m = types.ModuleType(name); m.__dict__.update(attrs); sys.modules[name] = m; return m


class _Col:
    def __eq__(self, o): return True
    def __ne__(self, o): return True
    def in_(self, o): return True
    def asc(self): return self
    def desc(self): return self
    def __ge__(self, o): return True
    def __hash__(self): return id(self)


def make_model(name, cols):
    def __init__(self, **kw): self.__dict__.update(kw)
    d = {c: _Col() for c in cols}; d["__init__"] = __init__
    return type(name, (), d)


class HTTPException(Exception):
    def __init__(self, status_code, detail=None):
        super().__init__(f"{status_code} {detail}")
        self.status_code, self.detail = status_code, detail


class _AnyRouter:
    def __getattr__(self, _): return lambda *a, **k: (lambda f: f)


class _AnyModule(types.ModuleType):
    def __getattr__(self, name):
        if name.startswith("__"): raise AttributeError(name)
        return type(name, (), {})


models = types.ModuleType("app.models")
models.Router = make_model("Router", ["id", "owner_id", "public_token"])
models.VoucherBatch = make_model("VoucherBatch", ["id", "router_id", "prix_unitaire", "created_at", "online_sale"])
models.Voucher = make_model("Voucher", ["id", "batch_id", "statut", "code"])
models.HotspotPurchase = make_model("HotspotPurchase", ["id", "router_id", "identifier", "telephone", "statut", "created_at", "voucher_id"])
models.User = make_model("User", ["id"])
sys.modules["app.models"] = models

schemas = _AnyModule("app.schemas"); sys.modules["app.schemas"] = schemas
stub("fastapi", APIRouter=lambda **k: _AnyRouter(), Depends=lambda x=None: None, HTTPException=HTTPException, Request=object,
     File=lambda *a, **k: None, UploadFile=object)
stub("fastapi.responses", StreamingResponse=object)
stub("sqlalchemy", func=MagicMock()); stub("sqlalchemy.orm", Session=object)
stub("slowapi", Limiter=lambda **k: MagicMock(limit=lambda *a, **k: (lambda f: f)))
stub("httpx", AsyncClient=MagicMock())
stub("app.database", get_db=None)
stub("app.dependencies", get_current_user=None)
stub("app.config", PAYGATE_AUTH_TOKEN="tok")
stub("app.crypto", decrypt=lambda x: x)
stub("app.routeros_client", RouterOSClient=object)
stub("app.pdf_generator", generate_vouchers_pdf=None)
stub("app.mikrotik_scripts", LOGIN_PAGE_ROUTER_FILE="x", render_login_page=None, DEFAULT_RATE_LIMIT="2M/2M")
stub("app.sync", sync_router=None)
import app; app.models, app.schemas = models, schemas

hotspot = importlib.import_module("app.routers.hotspot")
public = importlib.import_module("app.routers.hotspot_public")   # utilise le VRAI app.wireguard

NOW = datetime.utcnow()
ACTIVE = dict(trial_expires_at=None, subscription_expires_at=NOW + timedelta(days=5))
EXPIRED = dict(trial_expires_at=NOW - timedelta(days=1), subscription_expires_at=None)


def router(state, **extra):
    fields = dict(online_sales_enabled=True, code_prefix=None, code_length=8, code_digits_only=False)
    fields.update(state); fields.update(extra)
    return SimpleNamespace(id=1, nom="R", mikrotik_api_username="u", mikrotik_api_password="p", **fields)


class Chain:
    def __init__(self, db, target): self.db, self.target = db, target
    def __getattr__(self, name):
        if name in ("filter", "join", "group_by", "order_by"):
            return lambda *a, **k: self
        raise AttributeError(name)
    def first(self):
        self.db.queried.append(self.target)
        return self.db.rows.get(self.target)
    def all(self):
        self.db.queried.append(self.target)
        return []


class FakeDB:
    def __init__(self, **rows):
        self.rows, self.queried = {models.Router: rows.get("router"), models.VoucherBatch: rows.get("batch"),
                                   models.HotspotPurchase: rows.get("purchase"), models.Voucher: rows.get("voucher")}, []
    def query(self, target, *more): return Chain(self, target)
    def commit(self): pass
    def add(self, o): pass


class Passed(Exception):
    """Levée par notre faux client RouterOS : prouve qu'on a dépassé le blocage."""


def raises(status, fn):
    try:
        fn()
    except HTTPException as e:
        return e.status_code == status
    except Passed:
        return False
    return False


def run(coro): return asyncio.run(coro)


def _batch_data():
    return SimpleNamespace(profile_name="Ticket-1h", prix_unitaire=100.0, quantite=1, validite_jours=None, quota_mo=None)


def _call_generate(state):
    def _boom(_r): raise Passed()
    hotspot._client_for = _boom
    db = FakeDB(router=router(state))
    return lambda: run(hotspot.create_voucher_batch(1, _batch_data(), db, SimpleNamespace(id=9)))


# ---- Génération de tickets (propriétaire) ---------------------------------
def test_generate_batch_blocked_with_402_when_expired():
    assert raises(402, _call_generate(EXPIRED))


def test_generate_batch_message_tells_how_to_unlock():
    try:
        _call_generate(EXPIRED)()
    except HTTPException as e:
        assert "pack" in e.detail and "continuent de fonctionner" in e.detail


def test_generate_batch_allowed_when_subscription_active():
    try:
        _call_generate(ACTIVE)()
    except Passed:
        return
    raise AssertionError("le blocage s'est déclenché alors que l'abonnement est actif")


def test_generate_batch_allowed_during_trial():
    trial = dict(trial_expires_at=NOW + timedelta(days=2), subscription_expires_at=None)
    try:
        _call_generate(trial)()
    except Passed:
        return
    raise AssertionError("le blocage s'est déclenché pendant l'essai")


# ---- Page publique (client final) ----------------------------------------
def test_public_offers_empty_when_expired_and_no_stock_query():
    db = FakeDB(router=router(EXPIRED))
    assert public.list_offers(SimpleNamespace(), "tok", db) == []
    assert db.queried == [models.Router]   # n'a même pas cherché le stock


def test_public_offers_still_queries_stock_when_active():
    db = FakeDB(router=router(ACTIVE))
    assert public.list_offers(SimpleNamespace(), "tok", db) == []   # pas de stock : liste vide, mais...
    assert len(db.queried) == 2 and db.queried[0] is models.Router   # ...la requête de stock a bien eu lieu


def test_public_pay_blocked_with_403_when_expired():
    db = FakeDB(router=router(EXPIRED))
    data = SimpleNamespace(batch_id=1, telephone="90112233", methode="FLOOZ")
    assert raises(403, lambda: run(public.start_payment(SimpleNamespace(), "tok", data, db)))


def test_public_pay_not_blocked_when_active():
    db = FakeDB(router=router(ACTIVE), batch=None)   # lot introuvable => 404, donc le blocage est passé
    data = SimpleNamespace(batch_id=1, telephone="90112233", methode="FLOOZ")
    assert raises(404, lambda: run(public.start_payment(SimpleNamespace(), "tok", data, db)))


def test_public_payment_status_still_works_when_expired():
    """Un client qui a payé juste avant l'expiration doit toujours recevoir son code."""
    purchase = SimpleNamespace(statut="confirme", voucher_id=5)
    db = FakeDB(router=router(EXPIRED), purchase=purchase, voucher=SimpleNamespace(code="ABCD1234"))
    res = public.payment_status(SimpleNamespace(), "tok", "id-1", db)
    assert res == {"statut": "confirme", "code": "ABCD1234"}


def test_public_retrieve_code_not_blocked_when_expired():
    """« J'ai déjà payé » ne doit pas être bloqué : on doit passer l'accès au routeur sans 403/402."""
    db = FakeDB(router=router(EXPIRED))
    data = SimpleNamespace(telephone="90112233")
    try:
        public.retrieve_code(SimpleNamespace(), "tok", data, db)
    except HTTPException as e:
        assert e.status_code == 404 and "Aucun ticket" in e.detail   # « pas trouvé », pas « bloqué »


def test_public_offers_empty_when_owner_disabled_online_sales():
    db = FakeDB(router=router(ACTIVE, online_sales_enabled=False))
    assert public.list_offers(SimpleNamespace(), "tok", db) == []
    assert db.queried == [models.Router]   # n'a même pas cherché le stock


def test_public_pay_blocked_with_403_when_owner_disabled_online_sales():
    db = FakeDB(router=router(ACTIVE, online_sales_enabled=False))
    data = SimpleNamespace(batch_id=1, telephone="90112233", methode="FLOOZ")
    assert raises(403, lambda: run(public.start_payment(SimpleNamespace(), "tok", data, db)))


def test_public_pay_404_when_batch_not_sold_online():
    batch = SimpleNamespace(id=1, online_sale=False, prix_unitaire=100.0)
    db = FakeDB(router=router(ACTIVE), batch=batch)
    data = SimpleNamespace(batch_id=1, telephone="90112233", methode="FLOOZ")
    assert raises(404, lambda: run(public.start_payment(SimpleNamespace(), "tok", data, db)))


def test_webhook_confirmation_has_no_access_check():
    import pathlib, re
    src = pathlib.Path("app/routers/wallet.py").read_text(encoding="utf-8")
    assert not re.search(r"is_router_active|_require_active_router", src)


if __name__ == "__main__":
    ok = ko = 0
    for name, fn in sorted(list(globals().items())):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); ok += 1; print("PASS", name)
            except Exception as e:
                ko += 1; print("FAIL", name, repr(e))
    print(f"\n{ok} réussis, {ko} échoués")
    sys.exit(1 if ko else 0)
