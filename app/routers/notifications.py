from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.database import get_db
from app import models
from app.dependencies import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/")
def get_notifications(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    now = datetime.utcnow()
    notifications = []

    routers = db.query(models.Router).filter(models.Router.owner_id == current_user.id).all()

    for r in routers:
        trial_active = r.trial_expires_at and r.trial_expires_at > now
        sub_active = r.subscription_expires_at and r.subscription_expires_at > now

        expires_at = r.subscription_expires_at if sub_active else (r.trial_expires_at if trial_active else None)

        if expires_at:
            if expires_at - now <= timedelta(days=7):
                notifications.append({
                    "id": f"router-{r.id}-expiring",
                    "type": "expiring",
                    "title": f"{r.nom} expire bientôt",
                    "message": f"L'accès expire le {expires_at.strftime('%d/%m/%Y à %H:%M')}.",
                    "date": expires_at.isoformat(),
                })
        elif r.trial_expires_at or r.subscription_expires_at:
            dates = [d for d in [r.trial_expires_at, r.subscription_expires_at] if d]
            derniere_expiration = max(dates)
            notifications.append({
                "id": f"router-{r.id}-expired",
                "type": "expired",
                "title": f"{r.nom} — Accès expiré",
                "message": f"L'accès a expiré le {derniere_expiration.strftime('%d/%m/%Y')}. Activez un pack pour réactiver.",
                "date": derniere_expiration.isoformat(),
            })

    if current_user.role == "admin":
        il_24h = now - timedelta(hours=24)
        nouveaux = db.query(models.User).filter(models.User.created_at > il_24h).count()
        if nouveaux > 0:
            notifications.append({
                "id": f"admin-new-users-{now.date()}",
                "type": "info",
                "title": "Nouveaux utilisateurs",
                "message": f"{nouveaux} nouvelle(s) inscription(s) dans les dernières 24h.",
                "date": now.isoformat(),
            })

        expirent_bientot = db.query(models.Router).filter(
            models.Router.subscription_expires_at.isnot(None),
            models.Router.subscription_expires_at > now,
            models.Router.subscription_expires_at <= now + timedelta(days=7),
        ).count()
        if expirent_bientot > 0:
            notifications.append({
                "id": f"admin-expiring-{now.date()}",
                "type": "expiring",
                "title": "Abonnements clients à surveiller",
                "message": f"{expirent_bientot} routeur(s) client(s) expirent dans les 7 prochains jours.",
                "date": now.isoformat(),
            })

    return sorted(notifications, key=lambda n: n["date"])