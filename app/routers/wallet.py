import time
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.database import get_db
from app import models, schemas
from app.dependencies import get_current_user
from app.config import PAYGATE_AUTH_TOKEN
from app.limiter import limiter
router = APIRouter(prefix="/wallet", tags=["Portefeuille"])


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

    if current_user.solde < data.montant:
        raise HTTPException(status_code=400, detail="Solde insuffisant pour ce retrait.")

    reference = f"miabewifi-retrait-{current_user.id}-{int(time.time() * 1000)}"

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

    if result.get("status") != 200:
        raise HTTPException(
            status_code=400,
            detail=f"Le retrait a échoué auprès de l'opérateur (code {result.get('status')}).",
        )

    # Le transfert PayGate a réussi : on débite le solde et on trace la transaction
    current_user.solde -= data.montant
    transaction = models.Transaction(
        user_id=current_user.id,
        montant=data.montant,
        methode=data.network,
        statut="confirme",
        identifier=reference,
        type="retrait",
    )
    db.add(transaction)
    db.commit()

    return {"message": "Retrait effectué avec succès. Les fonds arrivent sur votre compte mobile money."}


@router.post("/webhook/paygate")
async def paygate_webhook(payload: dict, db: Session = Depends(get_db)):
    identifier = payload.get("identifier")
    tx_reference = payload.get("tx_reference")

    if not identifier or not tx_reference:
        return {"status": "ignored"}

    transaction = db.query(models.Transaction).filter(models.Transaction.identifier == identifier).first()
    if not transaction or transaction.statut == "confirme":
        return {"status": "ignored"}

    # Vérification server-to-server, comme sur wifi-hotspot
    async with httpx.AsyncClient() as client:
        verification = await client.post(
            "https://paygateglobal.com/api/v2/status",
            json={"auth_token": PAYGATE_AUTH_TOKEN, "identifier": identifier},
        )
        data = verification.json()

    if data.get("status") == 0:
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