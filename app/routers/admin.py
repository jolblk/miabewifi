from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from app.database import get_db
from app import models
from app.dependencies import get_current_admin

router = APIRouter(prefix="/admin", tags=["Administration"])


@router.get("/stats")
def get_global_stats(db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    now = datetime.utcnow()

    total_users = db.query(models.User).count()
    total_routers = db.query(models.Router).count()

    routers_actifs = db.query(models.Router).filter(
        (models.Router.trial_expires_at > now) | (models.Router.subscription_expires_at > now)
    ).count()

    revenus_total = db.query(func.sum(models.Transaction.montant)).filter(
        models.Transaction.type == "recharge", models.Transaction.statut == "confirme"
    ).scalar() or 0

    il_30j = now - timedelta(days=30)
    revenus_30j = db.query(func.sum(models.Transaction.montant)).filter(
        models.Transaction.type == "recharge",
        models.Transaction.statut == "confirme",
        models.Transaction.created_at > il_30j,
    ).scalar() or 0

    return {
        "total_users": total_users,
        "total_routers": total_routers,
        "routers_actifs": routers_actifs,
        "routers_inactifs": total_routers - routers_actifs,
        "revenus_total": revenus_total,
        "revenus_30j": revenus_30j,
    }


@router.get("/users")
def list_all_users(db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    users = db.query(models.User).order_by(models.User.created_at.desc()).all()
    result = []
    for u in users:
        nb_routers = db.query(models.Router).filter(models.Router.owner_id == u.id).count()
        result.append({
            "id": u.id,
            "nom": u.nom,
            "email": u.email,
            "role": u.role,
            "solde": u.solde,
            "nb_routers": nb_routers,
            "created_at": u.created_at,
        })
    return result


@router.get("/routers")
def list_all_routers(db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    routers = db.query(models.Router).order_by(models.Router.created_at.desc()).all()
    now = datetime.utcnow()
    result = []
    for r in routers:
        trial_actif = r.trial_expires_at and r.trial_expires_at > now
        abo_actif = r.subscription_expires_at and r.subscription_expires_at > now
        result.append({
            "id": r.id,
            "nom": r.nom,
            "proprietaire": r.owner.nom,
            "proprietaire_email": r.owner.email,
            "wireguard_ip": r.wireguard_ip,
            "is_connected": r.is_connected,
            "actif": trial_actif or abo_actif,
            "trial_expires_at": r.trial_expires_at,
            "subscription_expires_at": r.subscription_expires_at,
            "created_at": r.created_at,
        })
    return result


@router.get("/transactions")
def list_all_transactions(db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    transactions = db.query(models.Transaction).order_by(models.Transaction.created_at.desc()).limit(100).all()
    result = []
    for t in transactions:
        user = db.query(models.User).filter(models.User.id == t.user_id).first()
        result.append({
            "id": t.id,
            "user_nom": user.nom if user else "Inconnu",
            "montant": t.montant,
            "methode": t.methode,
            "statut": t.statut,
            "type": t.type,
            "identifier": t.identifier,
            "created_at": t.created_at,
        })
    return result


# --- Retraits à vérifier -------------------------------------------------------------------
# Un retrait passe en « a_verifier » quand PayGate n'a pas donné de réponse claire (coupure,
# délai dépassé...) : l'argent est peut-être parti. Le montant reste réservé (déjà retiré du
# solde) jusqu'à ce qu'un administrateur vérifie la référence dans le tableau de bord PayGate :
#   - l'argent est bien arrivé  -> « confirmer » : rien ne bouge, le retrait est validé ;
#   - l'argent n'est pas parti  -> « rembourser » : le montant est rendu au solde du client.


@router.get("/retraits-a-verifier")
def list_withdrawals_to_check(db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    rows = (
        db.query(models.Transaction, models.User)
        .join(models.User, models.Transaction.user_id == models.User.id)
        .filter(models.Transaction.type == "retrait", models.Transaction.statut == "a_verifier")
        .order_by(models.Transaction.created_at.asc())
        .all()
    )
    return [
        {
            "id": t.id,
            "identifier": t.identifier,
            "montant": t.montant,
            "methode": t.methode,
            "user_nom": u.nom,
            "user_email": u.email,
            "created_at": t.created_at,
        }
        for t, u in rows
    ]


def _claim_withdrawal_to_check(db: Session, transaction_id: int, new_statut: str) -> models.Transaction:
    """Passe un retrait de « a_verifier » à `new_statut` en une seule opération : si deux
    administrateurs cliquent en même temps, un seul des deux clics est pris en compte."""
    rows_updated = (
        db.query(models.Transaction)
        .filter(
            models.Transaction.id == transaction_id,
            models.Transaction.type == "retrait",
            models.Transaction.statut == "a_verifier",
        )
        .update({"statut": new_statut}, synchronize_session=False)
    )
    if rows_updated == 0:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ce retrait n'est plus à vérifier (déjà traité ?).")
    return db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()


@router.post("/retraits/{transaction_id}/confirmer")
def confirm_withdrawal(transaction_id: int, db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    """L'argent est bien arrivé chez le client (vérifié dans PayGate) : le retrait est validé."""
    _claim_withdrawal_to_check(db, transaction_id, "confirme")
    db.commit()
    return {"message": "Retrait confirmé."}


@router.post("/retraits/{transaction_id}/rembourser")
def refund_withdrawal(transaction_id: int, db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    """L'argent n'est PAS parti (vérifié dans PayGate) : le montant réservé est rendu au client."""
    transaction = _claim_withdrawal_to_check(db, transaction_id, "echoue")
    user = (
        db.query(models.User)
        .filter(models.User.id == transaction.user_id)
        .with_for_update()
        .first()
    )
    if user is None:
        db.rollback()
        raise HTTPException(status_code=404, detail="Client introuvable.")
    user.solde = (user.solde or 0) + transaction.montant
    db.commit()
    return {"message": "Retrait annulé : le montant a été rendu au client."}