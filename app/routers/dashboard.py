"""Tableau de bord : ventes du jour (tous routeurs) et alertes de stock."""
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app import models
from app.dashboard_summary import day_bounds, sales_by_router, stock_alerts
from app.database import get_db
from app.dependencies import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Tableau de bord"])


@router.get("/resume")
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    now = datetime.utcnow()
    yesterday_start, today_start, tomorrow_start = day_bounds(now)

    # Achats en ligne : payés par le client sur la page Wi-Fi (vente sans vendeur, « vendu_par » vide).
    online_sales = (
        db.query(models.VoucherBatch.router_id, models.Sale.montant, models.Sale.vendu_le)
        .join(models.Voucher, models.Sale.voucher_id == models.Voucher.id)
        .join(models.VoucherBatch, models.Voucher.batch_id == models.VoucherBatch.id)
        .filter(
            models.VoucherBatch.owner_id == current_user.id,
            models.Sale.vendu_par.is_(None),
            models.Sale.vendu_le >= yesterday_start,
            models.Sale.vendu_le < tomorrow_start,
        )
        .all()
    )
    # Tickets imprimés : comptés le jour de leur première connexion, au prix du lot
    # (tous les tickets utilisés, sauf ceux achetés en ligne, déjà comptés ci-dessus).
    printed_used = (
        db.query(models.VoucherBatch.router_id, models.VoucherBatch.prix_unitaire, models.Voucher.first_login_at)
        .select_from(models.Voucher)
        .join(models.VoucherBatch, models.Voucher.batch_id == models.VoucherBatch.id)
        .outerjoin(models.Sale, models.Sale.voucher_id == models.Voucher.id)
        .filter(
            models.VoucherBatch.owner_id == current_user.id,
            models.Voucher.first_login_at >= yesterday_start,
            models.Voucher.first_login_at < tomorrow_start,
            or_(models.Sale.id.is_(None), models.Sale.vendu_par.isnot(None)),
        )
        .all()
    )
    per_router = sales_by_router(list(online_sales) + list(printed_used), today_start)
    online_today = sales_by_router(online_sales, today_start)
    printed_today = sales_by_router(printed_used, today_start)

    # Stock par forfait vendu (même forfait, même prix, mêmes options), routeur par routeur.
    batches = (
        db.query(models.VoucherBatch)
        .filter(models.VoucherBatch.owner_id == current_user.id)
        .all()
    )
    counts = dict(
        db.query(models.Voucher.batch_id, func.count(models.Voucher.id))
        .join(models.VoucherBatch, models.Voucher.batch_id == models.VoucherBatch.id)
        .filter(models.VoucherBatch.owner_id == current_user.id)
        .group_by(models.Voucher.batch_id)
        .all()
    )
    available = dict(
        db.query(models.Voucher.batch_id, func.count(models.Voucher.id))
        .join(models.VoucherBatch, models.Voucher.batch_id == models.VoucherBatch.id)
        .outerjoin(models.Sale, models.Sale.voucher_id == models.Voucher.id)
        .filter(
            models.VoucherBatch.owner_id == current_user.id,
            models.Voucher.statut == "AVAILABLE",
            models.Sale.id.is_(None),
        )
        .group_by(models.Voucher.batch_id)
        .all()
    )
    from app.routers.hotspot_public import _batch_label

    groups = {}
    for b in batches:
        key = (b.router_id, b.profile_name, b.prix_unitaire, b.validite_jours, b.quota_mo)
        g = groups.setdefault(key, {
            "router_id": b.router_id,
            "profile_name": b.profile_name,
            "forfait": _batch_label(b),
            "prix": b.prix_unitaire,
            "disponibles": 0,
            "total": 0,
            "dernier_lot": None,
        })
        g["disponibles"] += available.get(b.id, 0)
        g["total"] += counts.get(b.id, 0)
        if b.created_at and (g["dernier_lot"] is None or b.created_at > g["dernier_lot"]):
            g["dernier_lot"] = b.created_at
    alerts = stock_alerts(list(groups.values()), now)

    return {
        "aujourdhui": sum(v["aujourdhui"] for v in per_router.values()),
        "hier": sum(v["hier"] for v in per_router.values()),
        "tickets_aujourdhui": sum(v["tickets"] for v in per_router.values()),
        "par_routeur": {str(k): v for k, v in per_router.items()},
        "en_ligne": {
            "montant": sum(v["aujourdhui"] for v in online_today.values()),
            "tickets": sum(v["tickets"] for v in online_today.values()),
        },
        "imprimes": {
            "montant": sum(v["aujourdhui"] for v in printed_today.values()),
            "tickets": sum(v["tickets"] for v in printed_today.values()),
        },
        "stock": [
            {k: a[k] for k in ("router_id", "profile_name", "forfait", "prix", "disponibles", "niveau")}
            for a in alerts
        ],
    }
