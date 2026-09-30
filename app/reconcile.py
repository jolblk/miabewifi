"""Rattrapage des paiements de tickets dont le webhook PayGate n'est jamais arrivé.

Normalement PayGate prévient le serveur (webhook) dès qu'un client a payé. Si cet appel
est perdu (coupure, redémarrage du serveur...), l'achat resterait « en attente » pour
toujours alors que le client a payé. Ici, toutes les quelques secondes, on redemande
directement à PayGate l'état des achats encore en attente, et on attribue le ticket
si le paiement est réussi.

La confirmation réutilise _confirm_hotspot_purchase (wallet.py) : elle est protégée contre
le double traitement, donc webhook et rattrapage peuvent arriver en même temps sans risque.
"""
import asyncio
import logging
from datetime import datetime, timedelta

import httpx

from app import models
from app.config import PAYGATE_AUTH_TOKEN, PURCHASE_RECONCILE_INTERVAL_SECONDS
from app.database import SessionLocal
from app.routers.wallet import _confirm_hotspot_purchase

logger = logging.getLogger("miabewifi.reconcile")

MIN_AGE = timedelta(seconds=20)       # laisse d'abord sa chance au webhook normal
FAST_WINDOW = timedelta(minutes=15)   # jusque-là : vérifié à chaque passage
SLOW_RECHECK = timedelta(minutes=10)  # ensuite : une vérification toutes les 10 minutes
MAX_AGE = timedelta(hours=6)          # au-delà, on abandonne (paiement jamais validé)

# Dernière vérification par achat (en mémoire : repart de zéro au redémarrage, sans gravité).
_last_checked: dict[int, datetime] = {}


async def _paygate_payment_succeeded(identifier: str) -> bool:
    """Demande à PayGate si ce paiement est réussi (status 0)."""
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            "https://paygateglobal.com/api/v2/status",
            json={"auth_token": PAYGATE_AUTH_TOKEN, "identifier": identifier},
        )
        return response.json().get("status") == 0


async def reconcile_pending_purchases(db, now: datetime | None = None) -> int:
    """Vérifie les achats en attente auprès de PayGate. Retourne le nombre d'achats confirmés."""
    now = now or datetime.utcnow()
    pending = (
        db.query(models.HotspotPurchase)
        .filter(
            models.HotspotPurchase.statut == "en_attente",
            models.HotspotPurchase.created_at <= now - MIN_AGE,
            models.HotspotPurchase.created_at >= now - MAX_AGE,
        )
        .order_by(models.HotspotPurchase.created_at.asc())
        .all()
    )

    confirmed = 0
    for purchase in pending:
        age = now - purchase.created_at
        last = _last_checked.get(purchase.id)
        if age > FAST_WINDOW and last is not None and now - last < SLOW_RECHECK:
            continue
        _last_checked[purchase.id] = now
        try:
            if not await _paygate_payment_succeeded(purchase.identifier):
                continue
            await _confirm_hotspot_purchase(db, purchase)
            confirmed += 1
            logger.info("Achat %s rattrapé (webhook manquant).", purchase.identifier)
        except Exception:
            db.rollback()
            logger.warning("Vérification impossible pour l'achat %s", purchase.identifier, exc_info=True)

    # Nettoie la mémoire : on oublie les achats qui ne sont plus en attente.
    still_pending = {p.id for p in pending}
    for purchase_id in list(_last_checked):
        if purchase_id not in still_pending:
            del _last_checked[purchase_id]
    return confirmed


async def reconcile_loop() -> None:
    if PURCHASE_RECONCILE_INTERVAL_SECONDS <= 0:
        logger.info("Rattrapage des paiements désactivé.")
        return
    while True:
        await asyncio.sleep(PURCHASE_RECONCILE_INTERVAL_SECONDS)
        db = SessionLocal()
        try:
            await reconcile_pending_purchases(db)
        except Exception:
            logger.exception("Erreur inattendue pendant le rattrapage des paiements")
        finally:
            db.close()