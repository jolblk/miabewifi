# Lancer depuis la racine du projet :  python tests/verify_wallet_sale_credit.py
# (volontairement nommé verify_* : pytest ne le charge pas, car il remplace des modules par des faux)
"""Vérification isolée (SANS base ni dépendances) : exécute la VRAIE fonction _confirm_hotspot_purchase de app/routers/wallet.py
avec une fausse base de données (SQLAlchemy/FastAPI/httpx absents de ce bac à sable)."""
import sys, types, asyncio, importlib
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, ".")

# ---- Faux modules lourds -------------------------------------------------
def stub(name, **attrs):
    m = types.ModuleType(name); m.__dict__.update(attrs); sys.modules[name] = m; return m

class _Col:                       # colonne factice : toute comparaison est autorisée
    def __eq__(self, o): return True
    def __ne__(self, o): return True
    def in_(self, o): return True
    def __hash__(self): return id(self)

def make_model(name, cols):
    def __init__(self, **kw): self.__dict__.update(kw)
    d = {c: _Col() for c in cols}; d["__init__"] = __init__
    return type(name, (), d)

models = types.ModuleType("app.models")
models.User = make_model("User", ["id", "solde"])
models.Router = make_model("Router", ["id", "owner_id"])
models.Voucher = make_model("Voucher", ["id", "batch_id", "statut"])
models.Sale = make_model("Sale", [])
models.Transaction = make_model("Transaction", ["id", "identifier", "statut"])
models.HotspotPurchase = make_model("HotspotPurchase", ["id", "statut", "identifier"])

stub("fastapi", APIRouter=lambda **k: MagicMock(post=lambda *a, **k: (lambda f: f), get=lambda *a, **k: (lambda f: f)),
     Depends=lambda x=None: None, HTTPException=Exception, Request=object, Query=lambda *a, **k: None)
stub("fastapi.responses", Response=object)
stub("app.security", verify_password=lambda plain, hashed: True)
stub("sqlalchemy"); stub("sqlalchemy.orm", Session=object)
stub("slowapi", Limiter=lambda **k: MagicMock(limit=lambda *a, **k: (lambda f: f)))
stub("slowapi.util", get_remote_address=lambda r: "x")
stub("httpx", AsyncClient=MagicMock())
stub("app.database", get_db=None)
stub("app.dependencies", get_current_user=None)
stub("app.config", PAYGATE_AUTH_TOKEN="tok", HOTSPOT_SALE_FEE_RATE="0.01", TELEGRAM_BOT_TOKEN=None, TELEGRAM_CHAT_ID=None)
stub("app.schemas", RechargeRequest=object, WithdrawRequest=object)
sys.modules["app.models"] = models
import app; app.models = models

wallet = importlib.import_module("app.routers.wallet")   # vrai fichier, vrai app.fees

# ---- Fausse base ---------------------------------------------------------
class FakeQuery:
    def __init__(self, db, target): self.db, self.target = db, target
    def filter(self, *a, **k): return self
    def with_for_update(self, **k): return self
    def update(self, *a, **k): return self.db.update_rowcount
    def first(self):
        if self.target is models.Voucher: return self.db.voucher
        if self.target is models.User: return self.db.owner
    def scalar(self): return self.db.owner_id

class FakeDB:
    def __init__(self, *, voucher, owner, owner_id=7, update_rowcount=1):
        self.voucher, self.owner, self.owner_id, self.update_rowcount = voucher, owner, owner_id, update_rowcount
        self.added, self.commits = [], 0
    def query(self, target, *more): return FakeQuery(self, target)
    def add(self, o): self.added.append(o)
    def commit(self): self.commits += 1

def purchase(montant=2000.0):
    return models.HotspotPurchase(id=1, batch_id=3, router_id=5, telephone="90112233", montant=montant,
                                  methode="FLOOZ", statut="en_attente", identifier="miabewifi-hs-5-1", voucher_id=None)

def run(db, p): asyncio.run(wallet._confirm_hotspot_purchase(db, p))

# ---- Tests ---------------------------------------------------------------
def test_sale_credits_owner_net_of_1_percent():
    owner = models.User(id=7, solde=500.0)
    voucher = models.Voucher(id=42, statut="AVAILABLE", code="ABCD1234")
    db, p = FakeDB(voucher=voucher, owner=owner), purchase(2000.0)
    run(db, p)
    assert owner.solde == 500.0 + 1980.0
    sale = next(o for o in db.added if isinstance(o, models.Sale))
    assert (sale.montant, sale.frais, sale.vendu_par) == (2000.0, 20.0, None)
    tx = next(o for o in db.added if isinstance(o, models.Transaction))
    assert (tx.user_id, tx.montant, tx.type, tx.statut) == (7, 1980.0, "vente", "confirme")
    assert tx.identifier == "miabewifi-hs-5-1-credit"
    assert voucher.statut == "USED" and p.statut == "confirme" and p.voucher_id == 42

def test_owner_with_none_balance_is_handled():
    owner = models.User(id=7, solde=None)
    db = FakeDB(voucher=models.Voucher(id=1, statut="AVAILABLE"), owner=owner)
    run(db, purchase(6000.0))
    assert owner.solde == 5940.0

def test_already_processed_webhook_credits_nothing():
    owner = models.User(id=7, solde=100.0)
    db = FakeDB(voucher=models.Voucher(id=1, statut="AVAILABLE"), owner=owner, update_rowcount=0)
    run(db, purchase())
    assert owner.solde == 100.0 and db.added == []

def test_out_of_stock_credits_nothing_and_refunds():
    owner = models.User(id=7, solde=100.0)
    db = FakeDB(voucher=None, owner=owner)
    p = purchase()
    # Faux PayGate qui accepte le remboursement (code 200)
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"status": 200}
    client = sys.modules["httpx"].AsyncClient.return_value.__aenter__.return_value
    client.post = AsyncMock(return_value=resp)
    run(db, p)
    assert owner.solde == 100.0
    assert not any(isinstance(o, (models.Sale, models.Transaction)) for o in db.added)
    assert p.statut == "rembourse"

def test_missing_owner_does_not_crash_and_sale_is_kept():
    voucher = models.Voucher(id=1, statut="AVAILABLE")
    db = FakeDB(voucher=voucher, owner=None, owner_id=None)
    p = purchase()
    run(db, p)
    assert p.statut == "confirme" and voucher.statut == "USED"
    assert not any(isinstance(o, models.Transaction) for o in db.added)

def test_single_final_commit_for_sale_credit_and_history():
    db = FakeDB(voucher=models.Voucher(id=1, statut="AVAILABLE"), owner=models.User(id=7, solde=0.0))
    run(db, purchase())
    assert db.commits == 2   # 1 = passage "en_cours", 2 = vente + crédit + historique ensemble


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
