import csv
import io
import logging
import time
import httpx
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.database import get_db
from app import models, schemas
from app.dependencies import get_current_user
from app.config import PAYGATE_AUTH_TOKEN, HOTSPOT_SALE_FEE_RATE
from app.fees import compute_sale_split
from app.payouts import SUCCES, ECHEC, classify_disburse_response
from app.alerts import alert_admins
from app.security import verify_password
from app import wallet_history

from app.limiter import limiter
router = APIRouter(prefix="/wallet", tags=["Portefeuille"])
logger = logging.getLogger("miabewifi.wallet")

# Délai d'attente des appels de décaissement PayGate. Le délai par défaut de httpx (5 s)
# est trop court : un décaissement mobile money peut prendre plus longtemps.
PAYGATE_DISBURSE_TIMEOUT = 30


async def _paygate_disburse(payload: dict) -> str:
    """Demande un décaissement à PayGate et renvoie SUCCES, ECHEC ou INCERTAIN
    (voir app/payouts.py). Ne lève jamais d'exception."""
    try:
        async with httpx.AsyncClient(timeout=PAYGATE_DISBURSE_TIMEOUT) as client:
            response = await client.post(
                "https://paygateglobal.com/api/v1/disburse",
                json={"auth_token": PAYGATE_AUTH_TOKEN, **payload},
            )
    except Exception:
        logger.exception("Décaissement PayGate sans réponse (référence %s)", payload.get("reference"))
        return classify_disburse_response(None, None)

    try:
        body = response.json()
    except Exception:
        body = None
    outcome = classify_disburse_response(response.status_code, body)
    if outcome != SUCCES:
        logger.warning(
            "Décaissement PayGate %s (référence %s) : HTTP %s, réponse %s",
            outcome, payload.get("reference"), response.status_code, body,
        )
    return outcome

@router.post("/recharger")
@limiter.limit("10/minute")
async def recharger(
    request: Request,
    data: schemas.RechargeRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    identifier = f"miabewifi-{current_user.id}-{int(time.time() * 1000)}"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://paygateglobal.com/api/v1/pay",
            json={
                "auth_token": PAYGATE_AUTH_TOKEN,
                "phone_number": data.phone_number,
                "amount": data.montant,
                "description": f"Recharge MIABEWIFI - {current_user.email}",
                "identifier": identifier,
                "network": data.network,
            },
        )
        result = response.json()

    if result.get("status") != 0:
        raise HTTPException(status_code=400, detail=f"Erreur PayGate (code {result.get('status')})")

    transaction = models.Transaction(
        user_id=current_user.id,
        montant=data.montant,
        methode=data.network,
        statut="en_attente",
        identifier=identifier,
        telephone=data.phone_number,
    )
    db.add(transaction)
    db.commit()

    return {"message": "Demande de paiement envoyée. Valide sur ton téléphone.", "identifier": identifier}


@router.post("/retirer")
@limiter.limit("5/minute")
async def retirer(
    request: Request,
    data: schemas.WithdrawRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if data.montant <= 0:
        raise HTTPException(status_code=400, detail="Montant invalide.")

    # Confirmation par mot de passe : un compte resté ouvert ou volé ne peut pas être vidé
    # d'un simple clic. (Limité à 5 essais par minute par le décorateur ci-dessus.)
    if not verify_password(data.password, current_user.hashed_password):
        raise HTTPException(status_code=403, detail="Mot de passe incorrect. Le retrait n'a pas été effectué.")

    reference = f"miabewifi-retrait-{current_user.id}-{int(time.time() * 1000)}"

    # Verrouille la ligne utilisateur et débite tout de suite (réservation des fonds).
    # Empêche deux retraits simultanés de dépasser le solde réellement disponible.
    current_user = (
        db.query(models.User)
        .filter(models.User.id == current_user.id)
        .with_for_update()
        .first()
    )
    if current_user.solde < data.montant:
        raise HTTPException(status_code=400, detail="Solde insuffisant pour ce retrait.")

    current_user.solde -= data.montant
    transaction = models.Transaction(
        user_id=current_user.id,
        montant=data.montant,
        methode=data.network,
        statut="en_attente",
        identifier=reference,
        type="retrait",
        telephone=data.phone_number,
    )
    db.add(transaction)
    db.commit()

    outcome = await _paygate_disburse({
        "phone_number": data.phone_number,
        "amount": data.montant,
        "reason": f"Retrait MIABEWIFI - {current_user.email}",
        "reference": reference,
        "network": data.network,
    })

    if outcome == SUCCES:
        transaction.statut = "confirme"
        db.commit()
        return {"message": "Retrait effectué avec succès. Les fonds arrivent sur votre compte mobile money."}

    if outcome == ECHEC:
        # PayGate a clairement refusé : l'argent n'est pas parti, on rembourse les fonds réservés.
        refund_user = (
            db.query(models.User)
            .filter(models.User.id == current_user.id)
            .with_for_update()
            .first()
        )
        refund_user.solde += data.montant
        transaction.statut = "echoue"
        db.commit()
        raise HTTPException(
            status_code=400,
            detail="Le retrait a été refusé par l'opérateur. Votre solde n'a pas été débité.",
        )

    # Résultat INCERTAIN (coupure, délai dépassé, réponse illisible) : l'argent est peut-être
    # parti. On NE rembourse PAS (risque de double paiement) : les fonds restent réservés et un
    # administrateur tranche après vérification dans le tableau de bord PayGate.
    transaction.statut = "a_verifier"
    db.commit()
    await alert_admins(
        "⚠️ Retrait MIABEWIFI à vérifier\n\n"
        f"Référence : {reference}\n"
        f"Client : {current_user.nom} ({current_user.email})\n"
        f"Montant : {data.montant} FCFA vers {data.phone_number} ({data.network})\n\n"
        "PayGate n'a pas donné de réponse claire. Vérifiez cette référence dans le tableau de bord "
        "PayGate, puis confirmez ou remboursez le retrait depuis l'admin (Transactions)."
    )
    return {
        "message": (
            "Votre retrait est en cours de vérification auprès de l'opérateur. "
            "Ne refaites pas la demande : le montant reste réservé et vous serez fixé rapidement."
        ),
        "statut": "a_verifier",
    }


async def _confirm_hotspot_purchase(db: Session, purchase: models.HotspotPurchase) -> None:
    """Réserve un ticket disponible du forfait payé et le marque vendu à ce numéro.
    En cas de rupture de stock au moment de la confirmation (rare : quelqu'un d'autre
    a pris le dernier ticket entre-temps), rembourse automatiquement le client.

    Une fois le ticket attribué, le portefeuille du propriétaire du routeur est crédité
    du montant de la vente moins les frais (HOTSPOT_SALE_FEE_RATE, 1 % par défaut). La vente,
    le crédit et la ligne d'historique sont enregistrés dans une seule transaction : soit
    tout réussit, soit rien n'est enregistré."""
    rows_updated = (
        db.query(models.HotspotPurchase)
        .filter(models.HotspotPurchase.id == purchase.id, models.HotspotPurchase.statut == "en_attente")
        .update({"statut": "en_cours"}, synchronize_session=False)
    )
    db.commit()
    if rows_updated == 0:
        return  # déjà traité par un autre appel webhook concurrent

    voucher = (
        db.query(models.Voucher)
        .filter(models.Voucher.batch_id == purchase.batch_id, models.Voucher.statut == "AVAILABLE")
        .with_for_update(skip_locked=True)
        .first()
    )

    if voucher is None:
        purchase.statut = "en_rupture"
        db.commit()
        outcome = await _paygate_disburse({
            "phone_number": purchase.telephone,
            "amount": purchase.montant,
            "reason": "Remboursement MIABEWIFI - ticket épuisé",
            "reference": f"{purchase.identifier}-remb",
            "network": purchase.methode,
        })
        if outcome == SUCCES:
            purchase.statut = "rembourse"
        else:
            # Refus OU résultat incertain : jamais de nouvelle tentative automatique (risque de
            # double remboursement). Un administrateur vérifie dans PayGate et rembourse à la main.
            purchase.statut = "echoue_remboursement"
            logger.error("Remboursement automatique non confirmé pour l'achat %s (%s)", purchase.identifier, outcome)
            await alert_admins(
                "⚠️ Remboursement de ticket à vérifier\n\n"
                f"Référence : {purchase.identifier}-remb\n"
                f"Montant : {purchase.montant} FCFA vers {purchase.telephone} ({purchase.methode})\n"
                f"Résultat PayGate : {outcome}\n\n"
                "Vérifiez dans le tableau de bord PayGate si le remboursement est parti ; sinon, "
                "remboursez le client manuellement."
            )
        db.commit()
        return

    voucher.statut = "USED"
    voucher.used_at = datetime.utcnow()

    frais, net = compute_sale_split(purchase.montant, HOTSPOT_SALE_FEE_RATE)
    db.add(models.Sale(
        voucher_id=voucher.id,
        montant=purchase.montant,
        frais=frais,
        vendu_par=None,
        acheteur_telephone=purchase.telephone,
    ))

    # Crédite le propriétaire du routeur (ligne verrouillée : pas de crédit perdu si deux
    # ventes sont confirmées en même temps, ni de conflit avec un retrait en cours).
    owner_id = db.query(models.Router.owner_id).filter(models.Router.id == purchase.router_id).scalar()
    owner = (
        db.query(models.User).filter(models.User.id == owner_id).with_for_update().first()
        if owner_id is not None else None
    )
    if owner is not None:
        owner.solde = (owner.solde or 0) + net
        db.add(models.Transaction(
            user_id=owner.id,
            montant=net,
            methode=purchase.methode,
            statut="confirme",
            type="vente",
            identifier=f"{purchase.identifier}-credit",
        ))
    else:
        logger.error("Propriétaire introuvable pour l'achat %s : aucun crédit effectué", purchase.identifier)

    purchase.statut = "confirme"
    purchase.voucher_id = voucher.id
    db.commit()

def _confirm_recharge(db: Session, transaction: models.Transaction) -> bool:
    """Crédite le portefeuille d'une recharge payée. Retourne False si la recharge a déjà
    été traitée (ou si ce n'est pas une recharge) : le crédit n'est alors pas refait.

    Le passage « en_attente » -> « confirme » et le crédit du solde sont enregistrés en une
    seule fois : soit les deux réussissent, soit aucun (pas de recharge marquée payée sans
    crédit). Utilisée par le webhook PayGate ET par le rattrapage (app/reconcile.py)."""
    if transaction.type != "recharge":
        return False

    rows_updated = (
        db.query(models.Transaction)
        .filter(models.Transaction.id == transaction.id, models.Transaction.statut == "en_attente")
        .update({"statut": "confirme"}, synchronize_session=False)
    )
    if rows_updated == 0:
        db.rollback()
        return False  # déjà traitée par un autre appel concurrent

    user = (
        db.query(models.User)
        .filter(models.User.id == transaction.user_id)
        .with_for_update()
        .first()
    )
    if user is None:
        db.rollback()
        logger.error("Utilisateur introuvable pour la recharge %s : aucun crédit effectué", transaction.identifier)
        return False

    user.solde = (user.solde or 0) + transaction.montant
    db.commit()
    return True

@router.post("/webhook/paygate")
@limiter.limit("120/minute")
async def paygate_webhook(request: Request, payload: dict, db: Session = Depends(get_db)):
    identifier = payload.get("identifier")
    tx_reference = payload.get("tx_reference")

    if not identifier or not tx_reference:
        return {"status": "ignored"}

    transaction = db.query(models.Transaction).filter(models.Transaction.identifier == identifier).first()
    purchase = None if transaction else (
        db.query(models.HotspotPurchase).filter(models.HotspotPurchase.identifier == identifier).first()
    )

    if not transaction and not purchase:
        return {"status": "ignored"}
    if transaction and transaction.statut == "confirme":
        return {"status": "ignored"}
    if purchase and purchase.statut != "en_attente":
        return {"status": "ignored"}

    # Vérification server-to-server, comme sur wifi-hotspot
    async with httpx.AsyncClient() as client:
        verification = await client.post(
            "https://paygateglobal.com/api/v2/status",
            json={"auth_token": PAYGATE_AUTH_TOKEN, "identifier": identifier},
        )
        data = verification.json()

    if data.get("status") != 0:
        return {"status": "ok"}

    if purchase:
        await _confirm_hotspot_purchase(db, purchase)
        return {"status": "ok"}

    if not _confirm_recharge(db, transaction):
        return {"status": "already_processed"}

    return {"status": "ok"}


@router.get("/solde")
def get_solde(current_user: models.User = Depends(get_current_user)):
    return {"solde": current_user.solde}

@router.get("/transactions")
def get_transactions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    transactions = (
        db.query(models.Transaction)
        .filter(models.Transaction.user_id == current_user.id)
        .order_by(models.Transaction.created_at.desc())
        .all()
    )
    return [
        {
            "id": t.id,
            "montant": t.montant,
            "methode": t.methode,
            "statut": t.statut,
            "type": t.type,
            "created_at": t.created_at,
        }
        for t in transactions
    ]


# --- Historique détaillé, bilan du mois, relevé, numéros déjà utilisés ---------------------

def _history_rows(db: Session, user_id: int, start: datetime | None = None, end: datetime | None = None):
    """Transactions du compte, avec le détail des ventes en ligne (forfait, frais, numéro)
    et le nom du routeur des abonnements. Du plus récent au plus ancien."""
    query = db.query(models.Transaction).filter(models.Transaction.user_id == user_id)
    if start is not None:
        query = query.filter(models.Transaction.created_at >= start, models.Transaction.created_at < end)
    transactions = query.order_by(models.Transaction.created_at.desc(), models.Transaction.id.desc()).all()

    # Ventes en ligne : la ligne de crédit s'appelle « <achat>-credit ».
    sale_ids = [t.identifier[: -len("-credit")] for t in transactions if t.type == "vente" and t.identifier.endswith("-credit")]
    purchases = {}
    if sale_ids:
        for purchase in db.query(models.HotspotPurchase).filter(models.HotspotPurchase.identifier.in_(sale_ids)).all():
            purchases[purchase.identifier] = purchase
    voucher_ids = [p.voucher_id for p in purchases.values() if p.voucher_id]
    sales = {}
    if voucher_ids:
        for sale in db.query(models.Sale).filter(models.Sale.voucher_id.in_(voucher_ids)).all():
            sales[sale.voucher_id] = sale
    batch_ids = {p.batch_id for p in purchases.values()}
    labels = {}
    if batch_ids:
        from app.routers.hotspot_public import _batch_label
        for batch in db.query(models.VoucherBatch).filter(models.VoucherBatch.id.in_(batch_ids)).all():
            labels[batch.id] = _batch_label(batch)

    # Abonnements : la ligne s'appelle « pack-<routeur>-<horodatage> ».
    router_ids = set()
    for t in transactions:
        if t.type == "debit" and t.identifier.startswith("pack-"):
            part = t.identifier.split("-")[1]
            if part.isdigit():
                router_ids.add(int(part))
    router_names = {}
    if router_ids:
        for r in db.query(models.Router).filter(models.Router.id.in_(router_ids), models.Router.owner_id == user_id).all():
            router_names[r.id] = r.nom

    rows = []
    for t in transactions:
        purchase = sale = forfait = router_name = None
        if t.type == "vente" and t.identifier.endswith("-credit"):
            purchase = purchases.get(t.identifier[: -len("-credit")])
            if purchase is not None:
                sale = sales.get(purchase.voucher_id)
                forfait = labels.get(purchase.batch_id)
        if t.type == "debit" and t.identifier.startswith("pack-"):
            part = t.identifier.split("-")[1]
            router_name = router_names.get(int(part)) if part.isdigit() else None
        rows.append(wallet_history.describe(t, sale=sale, purchase=purchase, forfait=forfait, router_name=router_name))
    return rows


@router.get("/historique")
def get_history(
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Historique lisible : libellés en français, numéros masqués, frais des ventes."""
    return _history_rows(db, current_user.id)[:limit]


@router.get("/resume")
def get_month_summary(
    mois: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Bilan d'un mois (le mois en cours par défaut) et montant réservé par des retraits
    en cours de vérification."""
    try:
        start, end = wallet_history.month_bounds(mois)
    except ValueError:
        raise HTTPException(status_code=400, detail="Mois invalide (format attendu : 2026-10).")
    rows = _history_rows(db, current_user.id, start, end)
    summary = wallet_history.month_summary((r["type"], r["statut"], r["montant"], r["frais"]) for r in rows)
    reserve = sum(
        t.montant
        for t in db.query(models.Transaction).filter(
            models.Transaction.user_id == current_user.id,
            models.Transaction.type == "retrait",
            models.Transaction.statut == "a_verifier",
        ).all()
    )
    return {"mois": start.strftime("%Y-%m"), "solde": current_user.solde, "reserve": reserve, **summary}


@router.get("/numeros")
def get_recent_numbers(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Numéros mobile money déjà utilisés pour un retrait ou une recharge réussis (5 au plus),
    pour les proposer au prochain retrait."""
    rows = (
        db.query(models.Transaction.telephone, models.Transaction.methode)
        .filter(
            models.Transaction.user_id == current_user.id,
            models.Transaction.telephone.isnot(None),
            models.Transaction.type.in_(["retrait", "recharge"]),
            models.Transaction.statut == "confirme",
        )
        .order_by(models.Transaction.created_at.desc())
        .limit(50)
        .all()
    )
    seen, numbers = set(), []
    for phone, methode in rows:
        if phone in seen or methode not in ("FLOOZ", "TMONEY"):
            continue
        seen.add(phone)
        numbers.append({"telephone": phone, "network": methode, "masque": wallet_history.mask_phone(phone)})
        if len(numbers) == 5:
            break
    return numbers


@router.get("/releve.csv")
def download_statement(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Relevé complet au format tableur (séparateur « ; », lisible directement par Excel)."""
    out = io.StringIO()
    writer = csv.writer(out, delimiter=";")
    writer.writerow(["Date", "Opération", "Détail", "Statut", "Montant (FCFA)", "Frais (FCFA)"])
    for r in _history_rows(db, current_user.id):
        writer.writerow([
            r["created_at"].strftime("%d/%m/%Y %H:%M") if r["created_at"] else "",
            r["titre"],
            r["detail"],
            r["statut"],
            r["montant_signe"],
            r["frais"] or "",
        ])
    filename = f"releve-miabewifi-{datetime.utcnow().strftime('%Y-%m-%d')}.csv"
    return Response(
        content="\ufeff" + out.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
