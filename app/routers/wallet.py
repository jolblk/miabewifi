import logging
import time
import httpx
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.database import get_db
from app import models, schemas
from app.dependencies import get_current_user
from app.config import PAYGATE_AUTH_TOKEN

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/wallet", tags=["Portefeuille"])
logger = logging.getLogger("miabewifi.wallet")

@router.post("/recharger")
async def recharger(
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
    )
    db.add(transaction)
    db.commit()

    return {"message": "Demande de paiement envoyée. Valide sur ton téléphone.", "identifier": identifier}


@router.post("/retirer")
async def retirer(
    data: schemas.WithdrawRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if data.montant <= 0:
        raise HTTPException(status_code=400, detail="Montant invalide.")

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
    )
    db.add(transaction)
    db.commit()

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://paygateglobal.com/api/v1/disburse",
                json={
                    "auth_token": PAYGATE_AUTH_TOKEN,
                    "phone_number": data.phone_number,
                    "amount": data.montant,
                    "reason": f"Retrait MIABEWIFI - {current_user.email}",
                    "reference": reference,
                    "network": data.network,
                },
            )
            result = response.json()
    except Exception:
        result = {"status": None}

    if result.get("status") != 200:
        # Échec chez PayGate : on rembourse les fonds réservés et on marque l'échec.
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
            detail=f"Le retrait a échoué auprès de l'opérateur (code {result.get('status')}).",
        )

    transaction.statut = "confirme"
    db.commit()

    return {"message": "Retrait effectué avec succès. Les fonds arrivent sur votre compte mobile money."}


async def _confirm_hotspot_purchase(db: Session, purchase: models.HotspotPurchase) -> None:
    """Réserve un ticket disponible du forfait payé et le marque vendu à ce numéro.
    En cas de rupture de stock au moment de la confirmation (rare : quelqu'un d'autre
    a pris le dernier ticket entre-temps), rembourse automatiquement le client."""
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
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    "https://paygateglobal.com/api/v1/disburse",
                    json={
                        "auth_token": PAYGATE_AUTH_TOKEN,
                        "phone_number": purchase.telephone,
                        "amount": purchase.montant,
                        "reason": "Remboursement MIABEWIFI - ticket épuisé",
                        "reference": f"{purchase.identifier}-remb",
                        "network": purchase.methode,
                    },
                )
            purchase.statut = "rembourse"
        except Exception:
            logger.error("Remboursement automatique impossible pour l'achat %s", purchase.identifier)
            purchase.statut = "echoue_remboursement"
        db.commit()
        return

    voucher.statut = "USED"
    voucher.used_at = datetime.utcnow()
    db.add(models.Sale(voucher_id=voucher.id, montant=purchase.montant, vendu_par=None, acheteur_telephone=purchase.telephone))
    purchase.statut = "confirme"
    purchase.voucher_id = voucher.id
    db.commit()


@router.post("/webhook/paygate")
@limiter.limit("30/minute")
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

    # Mise à jour atomique : ne réussit que si le statut est encore "en_attente".
    # Empêche un double crédit si deux appels webhook arrivent en même temps.
    rows_updated = (
        db.query(models.Transaction)
        .filter(
            models.Transaction.identifier == identifier,
            models.Transaction.statut != "confirme",
        )
        .update({"statut": "confirme"}, synchronize_session=False)
    )
    db.commit()

    if rows_updated == 0:
        # Une autre requête a déjà traité cette transaction entre-temps.
        return {"status": "already_processed"}

    user = db.query(models.User).filter(models.User.id == transaction.user_id).first()
    user.solde += transaction.montant
    db.commit()

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