"""Tableau de bord : ventes du jour (tous routeurs) et alertes de stock."""
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func
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

    sales = (
        db.query(models.VoucherBatch.router_id, models.Sale.montant, models.Sale.vendu_le)
        .join(models.Voucher, models.Sale.voucher_id == models.Voucher.id)
        .join(models.VoucherBatch, models.Voucher.batch_id == models.VoucherBatch.id)
        .filter(
            models.VoucherBatch.owner_id == current_user.id,
            models.Sale.vendu_le >= yesterday_start,
            models.Sale.vendu_le < tomorrow_start,
        )
        .all()
    )
    per_router = sales_by_router(sales, today_start)

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
        "stock": [
            {k: a[k] for k in ("router_id", "profile_name", "forfait", "prix", "disponibles", "niveau")}
            for a in alerts
        ],
    }
