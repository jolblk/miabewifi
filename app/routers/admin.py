from fastapi import APIRouter, Depends
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
            "created_at": t.created_at,
        })
    return result