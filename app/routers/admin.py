import logging
from datetime import datetime, timedelta
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app import models, platform_settings, wallet_history, wireguard
from app.admin_ops import (
    MAX_JOURS_OFFERTS,
    METHODE_ARRET,
    METHODE_OFFERT,
    check_adjustment,
    extended_expiry,
    subscription_kind,
)
from app.database import get_db
from app.dependencies import get_current_admin

router = APIRouter(prefix="/admin", tags=["Administration"])
logger = logging.getLogger("miabewifi.admin")


def _router_id_from_pack(identifier: str) -> int | None:
    """« pack-12-... » -> 12 (opérations d'abonnement)."""
    parts = (identifier or "").split("-")
    return int(parts[1]) if len(parts) > 2 and parts[0] == "pack" and parts[1].isdigit() else None


def _last_pack_methods(db: Session) -> dict[int, str]:
    """Pour chaque routeur, la méthode de la dernière opération d'abonnement (PACK, OFFERT, ARRET)."""
    rows = (
        db.query(models.Transaction.identifier, models.Transaction.methode)
        .filter(models.Transaction.type == "debit", models.Transaction.identifier.like("pack-%"))
        .order_by(models.Transaction.created_at.asc(), models.Transaction.id.asc())
        .all()
    )
    last = {}
    for identifier, methode in rows:
        router_id = _router_id_from_pack(identifier)
        if router_id is not None:
            last[router_id] = methode
    return last


# --- Vue d'ensemble --------------------------------------------------------------------------

@router.get("/stats")
def get_global_stats(db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    """Chiffres de la plateforme et liste des points à traiter."""
    now = datetime.utcnow()
    month_start = datetime(now.year, now.month, 1)

    routers = db.query(models.Router).all()
    actifs = [r for r in routers if (r.trial_expires_at and r.trial_expires_at > now)
              or (r.subscription_expires_at and r.subscription_expires_at > now)]
    abonnes_hors_ligne = [r for r in routers if r.subscription_expires_at and r.subscription_expires_at > now
                          and not r.is_connected]

    ventes_en_ligne = db.query(func.coalesce(func.sum(models.Sale.montant), 0)).filter(
        models.Sale.vendu_par.is_(None), models.Sale.vendu_le >= month_start,
    ).scalar()
    frais = db.query(func.coalesce(func.sum(models.Sale.frais), 0)).filter(
        models.Sale.vendu_le >= month_start,
    ).scalar()
    abonnements = db.query(func.coalesce(func.sum(models.Transaction.montant), 0)).filter(
        models.Transaction.type == "debit",
        models.Transaction.statut == "confirme",
        models.Transaction.methode == "PACK",
        models.Transaction.created_at >= month_start,
    ).scalar()

    frais_retraits = db.query(func.coalesce(func.sum(models.Transaction.frais), 0)).filter(
        models.Transaction.type == "retrait",
        models.Transaction.statut == "confirme",
        models.Transaction.created_at >= month_start,
    ).scalar()

    retraits = (
        db.query(models.Transaction)
        .filter(models.Transaction.type == "retrait", models.Transaction.statut == "a_verifier")
        .order_by(models.Transaction.created_at.asc())
        .all()
    )
    remboursements = (
        db.query(models.HotspotPurchase)
        .filter(models.HotspotPurchase.statut == "echoue_remboursement")
        .order_by(models.HotspotPurchase.created_at.asc())
        .all()
    )

    return {
        "total_users": db.query(models.User).count(),
        "total_routers": len(routers),
        "routers_actifs": len(actifs),
        "routers_en_ligne": sum(1 for r in routers if r.is_connected),
        "ventes_en_ligne_mois": ventes_en_ligne,
        "revenus_mois": abonnements + frais + frais_retraits,
        "abonnements_mois": abonnements,
        "frais_mois": frais,
        "frais_retraits_mois": frais_retraits,
        "adresses_libres": wireguard.count_free_ips(db, models),
        "retraits_a_verifier": len(retraits),
        "plus_ancien_retrait": retraits[0].created_at if retraits else None,
        "remboursements_a_faire": [
            {
                "identifier": p.identifier,
                "montant": p.montant,
                "reseau": wallet_history.network_label(p.methode),
                "telephone": p.telephone,
                "created_at": p.created_at,
            }
            for p in remboursements
        ],
        "abonnes_hors_ligne": [{"id": r.id, "nom": r.nom} for r in abonnes_hors_ligne],
    }


# --- Revendeurs ------------------------------------------------------------------------------

@router.get("/users")
def list_all_users(db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    counts = dict(
        db.query(models.Router.owner_id, func.count(models.Router.id)).group_by(models.Router.owner_id).all()
    )
    users = db.query(models.User).order_by(models.User.created_at.desc()).all()
    return [
        {
            "id": u.id,
            "nom": u.nom,
            "email": u.email,
            "role": u.role,
            "solde": u.solde,
            "nb_routers": counts.get(u.id, 0),
            "trial_used": bool(u.trial_used),
            "created_at": u.created_at,
        }
        for u in users
    ]


def _get_user(db: Session, user_id: int) -> models.User:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Revendeur introuvable.")
    return user


@router.get("/users/{user_id}")
def get_user_detail(user_id: int, db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    """Fiche d'un revendeur : ses routeurs et ses 50 dernières opérations."""
    from app.routers.wallet import _history_rows

    user = _get_user(db, user_id)
    now = datetime.utcnow()
    last = _last_pack_methods(db)
    routers = db.query(models.Router).filter(models.Router.owner_id == user.id).order_by(models.Router.created_at).all()
    return {
        "id": user.id,
        "nom": user.nom,
        "email": user.email,
        "role": user.role,
        "solde": user.solde,
        "trial_used": bool(user.trial_used),
        "created_at": user.created_at,
        "routers": [
            {
                "id": r.id,
                "nom": r.nom,
                "is_connected": r.is_connected,
                "abonnement": subscription_kind(r, last.get(r.id), now),
                "trial_expires_at": r.trial_expires_at,
                "subscription_expires_at": r.subscription_expires_at,
            }
            for r in routers
        ],
        "operations": _history_rows(db, user.id)[:50],
    }


class RoleUpdate(BaseModel):
    role: Literal["admin", "client"]


@router.post("/users/{user_id}/role")
def set_user_role(user_id: int, data: RoleUpdate, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    user = _get_user(db, user_id)
    if user.id == admin.id and data.role != "admin":
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas retirer vos propres droits d'administrateur.")
    user.role = data.role
    db.commit()
    logger.info("Rôle de %s passé à %s par %s", user.email, data.role, admin.email)
    return {"message": "Rôle mis à jour.", "role": user.role}


class BalanceAdjustment(BaseModel):
    montant: int = Field(ge=-10_000_000, le=10_000_000)  # positif = crédit, négatif = débit
    motif: str = Field(min_length=3, max_length=200)


@router.post("/users/{user_id}/ajustement")
def adjust_balance(user_id: int, data: BalanceAdjustment, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    """Corrige le solde d'un revendeur, avec un motif obligatoire, tracé dans son historique."""
    user = db.query(models.User).filter(models.User.id == user_id).with_for_update().first()
    if user is None:
        raise HTTPException(status_code=404, detail="Revendeur introuvable.")
    try:
        check_adjustment(user.solde or 0, data.montant, data.motif)
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    user.solde = (user.solde or 0) + data.montant
    db.add(models.Transaction(
        user_id=user.id,
        montant=data.montant,
        methode="ADMIN",
        statut="confirme",
        type="ajustement",
        identifier=f"ajustement-{user.id}-{int(datetime.utcnow().timestamp() * 1000)}",
        note=f"{data.motif.strip()} (par {admin.nom})",
    ))
    db.commit()
    logger.info("Solde de %s corrigé de %s F par %s : %s", user.email, data.montant, admin.email, data.motif)
    return {"message": "Solde corrigé.", "solde": user.solde}


# --- Routeurs --------------------------------------------------------------------------------

@router.get("/routers")
def list_all_routers(db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    now = datetime.utcnow()
    last = _last_pack_methods(db)
    routers = db.query(models.Router).order_by(models.Router.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "nom": r.nom,
            "proprietaire_id": r.owner_id,
            "proprietaire": r.owner.nom,
            "proprietaire_email": r.owner.email,
            "wireguard_ip": r.wireguard_ip,
            "is_connected": r.is_connected,
            "abonnement": subscription_kind(r, last.get(r.id), now),
            "actif": subscription_kind(r, last.get(r.id), now) in ("abonnement", "offert", "essai"),
            "trial_expires_at": r.trial_expires_at,
            "subscription_expires_at": r.subscription_expires_at,
            "created_at": r.created_at,
        }
        for r in routers
    ]


class GiftSubscription(BaseModel):
    jours: int = Field(ge=1, le=MAX_JOURS_OFFERTS)
    motif: Optional[str] = Field(default=None, max_length=200)


def _get_router(db: Session, router_id: int) -> models.Router:
    db_router = db.query(models.Router).filter(models.Router.id == router_id).first()
    if db_router is None:
        raise HTTPException(status_code=404, detail="Routeur introuvable.")
    return db_router


@router.post("/routers/{router_id}/offrir")
def gift_subscription(router_id: int, data: GiftSubscription, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    """Active ou prolonge l'abonnement d'un routeur gratuitement : le revendeur n'est pas débité.
    L'opération (0 F) apparaît dans son historique comme « Abonnement offert »."""
    db_router = _get_router(db, router_id)
    now = datetime.utcnow()
    db_router.subscription_expires_at = extended_expiry(db_router.subscription_expires_at, now, data.jours)
    motif = (data.motif or "").strip()
    db.add(models.Transaction(
        user_id=db_router.owner_id,
        montant=0,
        methode=METHODE_OFFERT,
        statut="confirme",
        type="debit",
        identifier=f"pack-{db_router.id}-offert-{int(now.timestamp() * 1000)}",
        note=f"{data.jours} jours offerts" + (f" : {motif}" if motif else "") + f" (par {admin.nom})",
    ))
    db.commit()
    logger.info("%s jours offerts au routeur %s par %s", data.jours, db_router.id, admin.email)
    return {"message": "Abonnement activé.", "subscription_expires_at": db_router.subscription_expires_at}


@router.post("/routers/{router_id}/arreter")
def stop_subscription(router_id: int, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    """Arrête tout de suite l'abonnement (et l'essai) d'un routeur. Rien n'est remboursé."""
    db_router = _get_router(db, router_id)
    now = datetime.utcnow()
    changed = False
    if db_router.subscription_expires_at and db_router.subscription_expires_at > now:
        db_router.subscription_expires_at = now
        changed = True
    if db_router.trial_expires_at and db_router.trial_expires_at > now:
        db_router.trial_expires_at = now
        changed = True
    if not changed:
        raise HTTPException(status_code=400, detail="Ce routeur n'a pas d'abonnement en cours.")
    db.add(models.Transaction(
        user_id=db_router.owner_id,
        montant=0,
        methode=METHODE_ARRET,
        statut="confirme",
        type="debit",
        identifier=f"pack-{db_router.id}-arret-{int(now.timestamp() * 1000)}",
        note=f"Arrêté par {admin.nom}",
    ))
    db.commit()
    logger.info("Abonnement du routeur %s arrêté par %s", db_router.id, admin.email)
    return {"message": "Abonnement arrêté."}


# --- Transactions ----------------------------------------------------------------------------

@router.get("/transactions")
def list_all_transactions(
    type: Optional[str] = Query(default=None, max_length=20),
    statut: Optional[str] = Query(default=None, max_length=20),
    q: Optional[str] = Query(default=None, max_length=100),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    query = db.query(models.Transaction, models.User).join(models.User, models.Transaction.user_id == models.User.id)
    if type:
        query = query.filter(models.Transaction.type == type)
    if statut:
        query = query.filter(models.Transaction.statut == statut)
    if q and q.strip():
        like = f"%{q.strip()}%"
        query = query.filter(or_(
            models.Transaction.identifier.ilike(like),
            models.User.nom.ilike(like),
            models.User.email.ilike(like),
        ))
    rows = query.order_by(models.Transaction.created_at.desc(), models.Transaction.id.desc()).limit(limit).all()

    router_ids = {rid for t, _ in rows if (rid := _router_id_from_pack(t.identifier)) is not None}
    names = dict(db.query(models.Router.id, models.Router.nom).filter(models.Router.id.in_(router_ids)).all()) if router_ids else {}
    result = []
    for t, u in rows:
        line = wallet_history.describe(t, router_name=names.get(_router_id_from_pack(t.identifier)))
        line.update({
            "user_id": u.id,
            "user_nom": u.nom,
            "identifier": t.identifier,
            "methode": t.methode,
            "note": t.note,
        })
        result.append(line)
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


# --- Réglages de la plateforme -------------------------------------------------------------

class FeeUpdate(BaseModel):
    frais_retrait_pourcent: float = Field(ge=0, le=20)


@router.get("/parametres")
def get_platform_settings(db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    percent = platform_settings.get_withdrawal_fee_percent(db)
    return {
        "frais_retrait_pourcent": platform_settings.percent_as_number(percent),
        "frais_retrait_max": platform_settings.percent_as_number(platform_settings.MAX_WITHDRAWAL_FEE_PERCENT),
    }


@router.put("/parametres")
def update_platform_settings(data: FeeUpdate, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    """Change le pourcentage de frais des retraits. S'applique aux retraits suivants uniquement."""
    try:
        percent = platform_settings.set_withdrawal_fee_percent(db, data.frais_retrait_pourcent, admin.email)
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    logger.info("Frais de retrait passés à %s %% par %s", percent, admin.email)
    return {"message": "Frais de retrait enregistrés.", "frais_retrait_pourcent": platform_settings.percent_as_number(percent)}
