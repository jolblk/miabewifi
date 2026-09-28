"""Synchronisation des tickets avec les routeurs MikroTik.

Toutes les quelques minutes (et à la demande), pour chaque routeur :
- détecte la 1re connexion réelle d'un ticket et calcule sa fin de validité calendaire ;
- passe en "EXPIRED" les tickets dont le temps de connexion est épuisé ou dont la
  validité est dépassée, et les supprime du routeur (ils ne peuvent plus servir).
"""
import asyncio
import logging
from datetime import datetime, timedelta

from app import models
from app.config import VOUCHER_SYNC_INTERVAL_SECONDS
from app.crypto import decrypt
from app.database import SessionLocal
from app.ros_utils import parse_ros_duration
from app.routeros_client import RouterOSClient

logger = logging.getLogger("miabewifi.sync")


def decide_voucher_update(
    *,
    now: datetime,
    first_login_at: datetime | None,
    expires_at: datetime | None,
    validite_jours: int | None,
    limit_seconds: int | None,
    ros_user: dict | None,
) -> dict:
    """Décide ce qu'il faut changer pour un ticket. Fonction pure (sans base ni réseau).

    Retourne un dict avec les clés :
      first_login_at / expires_at : nouvelles valeurs à enregistrer (ou absentes si inchangées)
      expire : True si le ticket doit passer en EXPIRED
      remove_from_router : True si son compte doit être supprimé du routeur
    """
    changes: dict = {"expire": False, "remove_from_router": False}

    if ros_user is None:
        # Le compte n'existe plus sur le routeur (supprimé, routeur réinitialisé) :
        # le ticket est inutilisable.
        changes["expire"] = True
        return changes

    uptime = parse_ros_duration(ros_user.get("uptime")) or 0

    if first_login_at is None and uptime > 0:
        # La connexion a eu lieu il y a au moins `uptime` secondes.
        first_login_at = now - timedelta(seconds=uptime)
        changes["first_login_at"] = first_login_at
        if validite_jours:
            expires_at = first_login_at + timedelta(days=validite_jours)
            changes["expires_at"] = expires_at

    time_exhausted = bool(limit_seconds) and uptime >= limit_seconds
    calendar_expired = expires_at is not None and now >= expires_at

    if time_exhausted or calendar_expired:
        changes["expire"] = True
        changes["remove_from_router"] = True

    return changes


async def sync_router(db, db_router: models.Router, client: RouterOSClient) -> dict:
    """Synchronise les tickets d'un routeur. Retourne un résumé chiffré."""
    vouchers = (
        db.query(models.Voucher)
        .join(models.VoucherBatch)
        .filter(models.VoucherBatch.router_id == db_router.id, models.Voucher.statut != "EXPIRED")
        .all()
    )
    summary = {"verifies": len(vouchers), "connexions_detectees": 0, "expires": 0}
    if not vouchers:
        return summary

    ros_users = {u.get("name"): u for u in await client.get_hotspot_users()}
    now = datetime.utcnow()
    to_remove: list[dict] = []

    for voucher in vouchers:
        batch = voucher.batch
        ros_user = ros_users.get(voucher.code)
        changes = decide_voucher_update(
            now=now,
            first_login_at=voucher.first_login_at,
            expires_at=voucher.expires_at,
            validite_jours=batch.validite_jours,
            limit_seconds=parse_ros_duration(batch.limit_uptime),
            ros_user=ros_user,
        )
        if "first_login_at" in changes:
            voucher.first_login_at = changes["first_login_at"]
            summary["connexions_detectees"] += 1
        if "expires_at" in changes:
            voucher.expires_at = changes["expires_at"]
        if changes["expire"]:
            voucher.statut = "EXPIRED"
            summary["expires"] += 1
        if changes["remove_from_router"] and ros_user is not None:
            to_remove.append(ros_user)

    db.commit()

    if to_remove:
        active_by_user = {}
        try:
            active_by_user = {a.get("user"): a for a in await client.get_active_sessions()}
        except Exception:
            logger.warning("Sessions actives illisibles sur le routeur %s", db_router.id)
        for ros_user in to_remove:
            try:
                session = active_by_user.get(ros_user.get("name"))
                if session:
                    await client.remove_active_session(session[".id"])
                await client.delete_hotspot_user(ros_user[".id"])
            except Exception:
                # Pas grave : le ticket est déjà marqué expiré côté MIABEWIFI,
                # le compte sera retenté à la prochaine synchro.
                logger.warning("Suppression du ticket %s impossible sur le routeur %s", ros_user.get("name"), db_router.id)
                _requeue_removal(db, ros_user.get("name"))
        db.commit()

    return summary


def _requeue_removal(db, code: str) -> None:
    """Si la suppression sur le routeur échoue, on garde le ticket "à revérifier"
    en le laissant hors du statut EXPIRED, pour que la prochaine synchro réessaie."""
    voucher = db.query(models.Voucher).filter(models.Voucher.code == code).first()
    if voucher and voucher.statut == "EXPIRED":
        voucher.statut = "USED" if voucher.sale else "AVAILABLE"


async def sync_all_routers() -> None:
    db = SessionLocal()
    try:
        router_ids = [
            rid
            for (rid,) in db.query(models.VoucherBatch.router_id)
            .join(models.Voucher)
            .filter(models.Voucher.statut != "EXPIRED")
            .distinct()
            .all()
        ]
        for rid in router_ids:
            db_router = db.query(models.Router).filter(models.Router.id == rid).first()
            if not db_router or not db_router.mikrotik_api_username or not db_router.mikrotik_api_password:
                continue
            try:
                async with RouterOSClient(
                    db_router.wireguard_ip,
                    db_router.mikrotik_api_username,
                    decrypt(db_router.mikrotik_api_password),
                ) as client:
                    await asyncio.wait_for(sync_router(db, db_router, client), timeout=60)
            except Exception as e:
                db.rollback()
                logger.warning("Synchro du routeur %s impossible : %s", rid, e)
    finally:
        db.close()


async def sync_loop() -> None:
    if VOUCHER_SYNC_INTERVAL_SECONDS <= 0:
        logger.info("Synchronisation des tickets désactivée.")
        return
    while True:
        try:
            await sync_all_routers()
        except Exception:
            logger.exception("Erreur inattendue pendant la synchronisation des tickets")
        await asyncio.sleep(VOUCHER_SYNC_INTERVAL_SECONDS)
