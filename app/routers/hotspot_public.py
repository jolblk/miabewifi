"""Routes PUBLIQUES (sans authentification) appelées par la page de connexion HotSpot
(app/templates/hotspot_login.html) pour le paiement de tickets en libre-service.

Le routeur est identifié par son `public_token` (dans l'URL), jamais par son id.
Le webhook PayGate (app/routers/wallet.py) confirme ensuite l'achat et attribue le ticket.

Endpoints :
  GET  /public/hotspot/{token}/forfaits          -> liste des forfaits en stock
  POST /public/hotspot/{token}/pay               -> lance le paiement mobile money
  GET  /public/hotspot/{token}/pay/{identifier}  -> statut d'un paiement (+ code si confirmé)
  POST /public/hotspot/{token}/retrieve          -> retrouve le dernier ticket payé avec ce numéro
"""
import logging
import secrets
import time
from datetime import datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from slowapi import Limiter
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import PAYGATE_AUTH_TOKEN
from app.database import get_db
from app.payment_guard import PHONE_LIMIT_MESSAGE, longest_window, phone_request_allowed
from app.ros_utils import format_duration_fr, format_quota_fr, parse_ros_duration
from app.wireguard import is_router_active

logger = logging.getLogger("miabewifi.hotspot_public")

from app.limiter import limiter, hotspot_key, payment_key
router = APIRouter(prefix="/public/hotspot", tags=["HotSpot public"])

# Statuts d'achat renvoyés tels quels au client ; "en_cours" (traitement interne) est
# présenté comme "en_attente" pour que la page continue simplement d'attendre.
_PENDING_STATUSES = {"en_attente", "en_cours"}


def _get_router_by_token(token: str, db: Session) -> models.Router:
    if not token:
        raise HTTPException(status_code=404, detail="Routeur introuvable.")
    db_router = db.query(models.Router).filter(models.Router.public_token == token).first()
    if not db_router:
        raise HTTPException(status_code=404, detail="Routeur introuvable.")
    return db_router


def _normalize_phone(phone: str) -> str:
    """Numéro local sans '+' ni indicatif Togo (228), pour PayGate et pour retrouver
    un achat quelle que soit la façon dont le client a saisi son numéro."""
    digits = phone.strip().lstrip("+")
    if digits.startswith("228") and len(digits) == 11:
        digits = digits[3:]
    return digits



def _normalize_mac(mac: str | None) -> str | None:
    """Adresse MAC au format unique AA:BB:CC:DD:EE:FF (ou None si absente)."""
    if not mac:
        return None
    return mac.strip().upper().replace("-", ":")


# « J'ai déjà payé » ne retrouve que les achats récents : c'est fait pour le client dont la
# page s'est fermée avant l'affichage du code, pas pour consulter d'anciens tickets.
RETRIEVE_WINDOW = timedelta(hours=24)

RETRIEVE_NOT_FOUND = (
    "Aucun ticket récent trouvé pour ce numéro sur cet appareil. Utilisez le téléphone qui a "
    "servi au paiement, ou demandez votre code à l'agent sur place."
)

def _batch_label(batch: models.VoucherBatch) -> str:
    if batch.limit_uptime:
        return format_duration_fr(parse_ros_duration(batch.limit_uptime))
    if batch.validite_jours:
        return f"{batch.validite_jours} j"
    return batch.profile_name

@router.get("/{token}/pages/{name}")
@limiter.limit("60/minute")
def get_hotspot_page(request: Request, token: str, name: str, db: Session = Depends(get_db)):
    """Page HotSpot personnalisée de ce routeur, téléchargée par le routeur lui-même quand
    l'écriture directe par l'API échoue. Ne contient rien de plus que ce que voit tout
    visiteur du Wi-Fi."""
    from app.mikrotik_scripts import HOTSPOT_PAGES, render_hotspot_pages

    if name not in HOTSPOT_PAGES:
        raise HTTPException(status_code=404, detail="Page inconnue.")
    db_router = _get_router_by_token(token, db)
    return Response(
        content=render_hotspot_pages(db_router)[name].encode("utf-8"),
        media_type="text/html; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/{token}/background.jpg")
@limiter.limit("120/minute")
def get_background(request: Request, token: str, db: Session = Depends(get_db)):
    """Photo de fond de la page de connexion de ce routeur (JPEG réduit).
    Gardée en cache 30 jours par les téléphones : l'adresse change à chaque nouvelle photo."""
    row = (
        db.query(models.Router.brand_background)
        .filter(models.Router.public_token == token)
        .first()
    )
    if not row or not row[0]:
        raise HTTPException(status_code=404, detail="Pas de photo de fond.")
    return Response(
        content=row[0],
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=2592000"},
    )

@router.get("/{token}/forfaits")
@limiter.limit("120/minute", key_func=hotspot_key)
def list_offers(request: Request, token: str, db: Session = Depends(get_db)):
    """Forfaits achetables : un par (forfait, prix, durée), uniquement s'il reste des tickets."""
    db_router = _get_router_by_token(token, db)
    if not is_router_active(db_router) or not db_router.online_sales_enabled:
        return []  # vente en ligne suspendue : la page affiche « Aucun forfait disponible »

    stock_rows = (
        db.query(models.Voucher.batch_id, func.count(models.Voucher.id))
        .join(models.VoucherBatch, models.Voucher.batch_id == models.VoucherBatch.id)
        .filter(
            models.VoucherBatch.router_id == db_router.id,
            models.VoucherBatch.online_sale == True,  # noqa: E712 - lots que le client propose en ligne
            models.Voucher.statut == "AVAILABLE",
        )
        .group_by(models.Voucher.batch_id)
        .all()
    )
    in_stock = {batch_id for batch_id, count in stock_rows if count > 0}
    if not in_stock:
        return []

    batches = (
        db.query(models.VoucherBatch)
        .filter(models.VoucherBatch.id.in_(in_stock))
        .order_by(models.VoucherBatch.prix_unitaire.asc(), models.VoucherBatch.created_at.asc())
        .all()
    )

    offers = []
    seen = set()
    for batch in batches:
        key = (batch.profile_name, batch.prix_unitaire, batch.limit_uptime, batch.validite_jours, batch.quota_mo)
        if key in seen:
            continue  # plusieurs lots du même forfait : on n'en propose qu'un
        seen.add(key)
        offers.append({
            "batch_id": batch.id,
            "duree": _batch_label(batch),
            "quota": format_quota_fr(batch.quota_mo),
            "prix": int(batch.prix_unitaire) if float(batch.prix_unitaire).is_integer() else batch.prix_unitaire,
        })
    return offers


@router.post("/{token}/pay")
@limiter.limit("20/minute", key_func=hotspot_key)
async def start_payment(
    request: Request,
    token: str,
    data: schemas.PublicHotspotPayRequest,
    db: Session = Depends(get_db),
):
    db_router = _get_router_by_token(token, db)
    # Seul le LANCEMENT d'un nouveau paiement est bloqué. Un client qui a déjà payé juste avant
    # l'expiration reçoit quand même son ticket (webhook, statut, « J'ai déjà payé »).
    if not is_router_active(db_router) or not db_router.online_sales_enabled:
        raise HTTPException(
            status_code=403,
            detail="La vente en ligne est momentanément indisponible sur ce Wi-Fi. Contactez l'agent sur place.",
        )

    batch = (
        db.query(models.VoucherBatch)
        .filter(models.VoucherBatch.id == data.batch_id, models.VoucherBatch.router_id == db_router.id)
        .first()
    )
    if not batch or not batch.online_sale:
        raise HTTPException(status_code=404, detail="Forfait introuvable.")

    available = (
        db.query(func.count(models.Voucher.id))
        .filter(models.Voucher.batch_id == batch.id, models.Voucher.statut == "AVAILABLE")
        .scalar()
    )
    if not available:
        raise HTTPException(status_code=409, detail="Ce forfait est épuisé pour le moment.")

    telephone = _normalize_phone(data.telephone)

    # Pas plus de quelques demandes vers un même numéro (voir app/payment_guard.py).
    now = datetime.utcnow()
    recent_requests = [
        created_at
        for (created_at,) in db.query(models.HotspotPurchase.created_at).filter(
            models.HotspotPurchase.telephone == telephone,
            models.HotspotPurchase.statut != "echoue",
            models.HotspotPurchase.created_at >= now - longest_window(),
        )
    ]
    if not phone_request_allowed(recent_requests, now):
        logger.warning("Demandes de paiement répétées vers %s refusées (routeur %s)", telephone, db_router.id)
        raise HTTPException(status_code=429, detail=PHONE_LIMIT_MESSAGE)

    # Identifiant imprévisible : il donne accès au statut (et au code) de l'achat.
    identifier = f"miabewifi-hs-{db_router.id}-{int(time.time() * 1000)}-{secrets.token_hex(6)}"

    # Le montant vient TOUJOURS de la base, jamais du client.
    purchase = models.HotspotPurchase(
        router_id=db_router.id,
        batch_id=batch.id,
        telephone=telephone,
        montant=batch.prix_unitaire,
        methode=data.methode,
        statut="en_attente",
        identifier=identifier,
        client_mac=_normalize_mac(data.mac),
    )
    db.add(purchase)
    db.commit()

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                "https://paygateglobal.com/api/v1/pay",
                json={
                    "auth_token": PAYGATE_AUTH_TOKEN,
                    "phone_number": telephone,
                    "amount": batch.prix_unitaire,
                    "description": f"Ticket Wi-Fi MIABEWIFI - {db_router.nom}",
                    "identifier": identifier,
                    "network": data.methode,
                },
            )
            result = response.json()
    except Exception:
        logger.exception("PayGate injoignable pour l'achat %s", identifier)
        purchase.statut = "echoue"
        db.commit()
        raise HTTPException(status_code=502, detail="Service de paiement indisponible. Réessayez.")

    if result.get("status") != 0:
        purchase.statut = "echoue"
        db.commit()
        raise HTTPException(status_code=400, detail=f"Le paiement n'a pas pu être lancé (code {result.get('status')}).")

    return {"identifier": identifier}


@router.get("/{token}/pay/{identifier}")
# 30/min par paiement (la page en fait 15) ; 600/min pour tout le hotspot = ~40 clients en attente
# en même temps, tout en empêchant d'essayer des identifiants au hasard.
@limiter.limit("30/minute", key_func=payment_key)
@limiter.limit("600/minute", key_func=hotspot_key)
def payment_status(request: Request, token: str, identifier: str, db: Session = Depends(get_db)):
    db_router = _get_router_by_token(token, db)

    purchase = (
        db.query(models.HotspotPurchase)
        .filter(models.HotspotPurchase.identifier == identifier, models.HotspotPurchase.router_id == db_router.id)
        .first()
    )
    if not purchase:
        raise HTTPException(status_code=404, detail="Paiement introuvable.")

    code = None
    if purchase.statut == "confirme" and purchase.voucher_id:
        voucher = db.query(models.Voucher).filter(models.Voucher.id == purchase.voucher_id).first()
        code = voucher.code if voucher else None

    statut = "en_attente" if purchase.statut in _PENDING_STATUSES else purchase.statut
    return {"statut": statut, "code": code}


@router.post("/{token}/retrieve")
@limiter.limit("30/minute", key_func=hotspot_key)
def retrieve_code(
    request: Request,
    token: str,
    data: schemas.PublicHotspotRetrieveRequest,
    db: Session = Depends(get_db),
):

    """Redonne le code du dernier ticket payé avec ce numéro sur ce routeur
    (client dont la page s'est fermée avant l'affichage du code).

    Sécurité : le numéro de téléphone seul ne suffit pas (n'importe qui peut connaître le
    numéro d'un voisin). Il faut AUSSI l'adresse MAC de l'appareil qui a payé, que la page
    HotSpot envoie automatiquement, et l'achat doit dater de moins de 24 h."""
    db_router = _get_router_by_token(token, db)
    telephone = _normalize_phone(data.telephone)
    mac = _normalize_mac(data.mac)
    if not mac:
        # Ancienne page de connexion (sans adresse MAC) ou page ouverte hors du HotSpot.
        raise HTTPException(status_code=404, detail=RETRIEVE_NOT_FOUND)

    since = datetime.utcnow() - RETRIEVE_WINDOW
    row = (
        db.query(models.HotspotPurchase, models.Voucher)
        .join(models.Voucher, models.HotspotPurchase.voucher_id == models.Voucher.id)
        .filter(
            models.HotspotPurchase.router_id == db_router.id,
            models.HotspotPurchase.telephone == telephone,
            models.HotspotPurchase.client_mac == mac,
            models.HotspotPurchase.statut == "confirme",
            models.HotspotPurchase.created_at >= since,
            models.Voucher.statut != "EXPIRED",
        )
        .order_by(models.HotspotPurchase.created_at.desc())
        .first()
    )
    if row:
        return {"code": row[1].code}

    recent_pending = (
        db.query(models.HotspotPurchase.id)
        .filter(
            models.HotspotPurchase.router_id == db_router.id,
            models.HotspotPurchase.telephone == telephone,
            models.HotspotPurchase.client_mac == mac,
            models.HotspotPurchase.statut.in_(_PENDING_STATUSES),
            models.HotspotPurchase.created_at >= datetime.utcnow() - timedelta(minutes=15),
        )
        .first()
    )
    if recent_pending:
        raise HTTPException(status_code=404, detail="Paiement en cours de confirmation, réessayez dans un instant.")
    raise HTTPException(status_code=404, detail=RETRIEVE_NOT_FOUND)