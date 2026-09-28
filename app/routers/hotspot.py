import asyncio
import io
import logging
import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app import models, schemas
from app.crypto import decrypt
from app.routeros_client import RouterOSClient
from app.pdf_generator import generate_vouchers_pdf
from app.mikrotik_scripts import LOGIN_PAGE_ROUTER_FILE, load_login_page
from app.sync import sync_router

logger = logging.getLogger("miabewifi.hotspot")

router = APIRouter(prefix="/hotspot", tags=["HotSpot"])

# Nombre de créations de tickets envoyées en parallèle au routeur.
ROUTER_CONCURRENCY = 5


def _get_authorized_router(router_id: int, db: Session, current_user: models.User) -> models.Router:
    db_router = (
        db.query(models.Router)
        .filter(models.Router.id == router_id, models.Router.owner_id == current_user.id)
        .first()
    )
    if not db_router:
        raise HTTPException(status_code=404, detail="Routeur introuvable.")

    if not db_router.mikrotik_api_username or not db_router.mikrotik_api_password:
        raise HTTPException(status_code=400, detail="Identifiants API MikroTik non configurés pour ce routeur.")

    return db_router


def _client_for(db_router: models.Router) -> RouterOSClient:
    return RouterOSClient(
        router_ip=db_router.wireguard_ip,
        username=db_router.mikrotik_api_username,
        password=decrypt(db_router.mikrotik_api_password),
    )


@router.get("/{router_id}/users")
async def list_hotspot_users(
    router_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_router = _get_authorized_router(router_id, db, current_user)
    try:
        async with _client_for(db_router) as client:
            return await client.get_hotspot_users()
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Impossible de joindre le MikroTik. Vérifiez que ce routeur est bien en RouterOS v7 ou plus récent. Détail technique : {e}",
        )


@router.get("/{router_id}/profiles")
async def list_hotspot_profiles(
    router_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_router = _get_authorized_router(router_id, db, current_user)
    try:
        async with _client_for(db_router) as client:
            return await client.get_hotspot_profiles()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Impossible de joindre le MikroTik : {e}")


@router.get("/{router_id}/sessions")
async def list_active_sessions(
    router_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_router = _get_authorized_router(router_id, db, current_user)
    try:
        async with _client_for(db_router) as client:
            return await client.get_active_sessions()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Impossible de joindre le MikroTik : {e}")


def _generate_voucher_code() -> str:
    return secrets.token_hex(4).upper()  # ex: "A1B2C3D4"


def _generate_unique_codes(db: Session, quantite: int) -> list[str]:
    """Génère `quantite` codes qui n'existent ni dans le lot ni déjà en base."""
    codes: set[str] = set()
    while len(codes) < quantite:
        candidates = {_generate_voucher_code() for _ in range(quantite - len(codes))} - codes
        taken = {
            c for (c,) in db.query(models.Voucher.code).filter(models.Voucher.code.in_(candidates)).all()
        }
        codes |= candidates - taken
    return list(codes)


async def _remove_users_from_router(client: RouterOSClient, codes: list[str]) -> None:
    """Annule la création de tickets sur le routeur (meilleur effort, sans jamais lever d'erreur)."""
    if not codes:
        return
    try:
        wanted = set(codes)
        users = await client.get_hotspot_users()
        sem = asyncio.Semaphore(ROUTER_CONCURRENCY)

        async def _delete(user_id: str):
            async with sem:
                await client.delete_hotspot_user(user_id)

        await asyncio.gather(
            *[_delete(u[".id"]) for u in users if u.get("name") in wanted],
            return_exceptions=True,
        )
    except Exception:
        logger.warning("Nettoyage des tickets impossible sur le routeur", exc_info=True)

async def _delete_codes_from_router(client: RouterOSClient, codes: list[str]) -> None:
    """Supprime ces codes du routeur s'ils y existent encore (idempotent).
    Lève une erreur si une suppression échoue : mieux vaut ne rien retirer en base
    que de perdre la trace d'un ticket qui reste actif sur le routeur."""
    if not codes:
        return
    wanted = set(codes)
    users = await client.get_hotspot_users()
    to_delete = [u for u in users if u.get("name") in wanted]
    if not to_delete:
        return  # déjà absents du routeur (routeur réinitialisé, etc.)

    active_by_user = {}
    try:
        active_by_user = {a.get("user"): a for a in await client.get_active_sessions()}
    except Exception:
        pass  # pas grave : couper la session immédiate n'est pas garanti, la suppression du compte suffit

    sem = asyncio.Semaphore(ROUTER_CONCURRENCY)

    async def _delete(u: dict):
        async with sem:
            session = active_by_user.get(u.get("name"))
            if session:
                try:
                    await client.remove_active_session(session[".id"])
                except Exception:
                    pass
            await client.delete_hotspot_user(u[".id"])

    results = await asyncio.gather(*[_delete(u) for u in to_delete], return_exceptions=True)
    errors = [r for r in results if isinstance(r, Exception)]
    if errors:
        raise errors[0]


def _get_authorized_voucher(voucher_id: int, db: Session, current_user: models.User) -> models.Voucher:
    voucher = (
        db.query(models.Voucher)
        .join(models.VoucherBatch)
        .filter(models.Voucher.id == voucher_id, models.VoucherBatch.owner_id == current_user.id)
        .first()
    )
    if not voucher:
        raise HTTPException(status_code=404, detail="Ticket introuvable.")
    return voucher


def _get_authorized_batch(batch_id: int, db: Session, current_user: models.User) -> models.VoucherBatch:
    batch = (
        db.query(models.VoucherBatch)
        .filter(models.VoucherBatch.id == batch_id, models.VoucherBatch.owner_id == current_user.id)
        .first()
    )
    if not batch:
        raise HTTPException(status_code=404, detail="Lot de tickets introuvable.")
    return batch

@router.post("/{router_id}/vouchers", response_model=schemas.VoucherBatchOut)
async def create_voucher_batch(
    router_id: int,
    data: schemas.VoucherBatchCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Génère un lot de tickets. Tout ou rien : si un seul ticket ne peut pas être créé
    sur le routeur, ceux déjà créés sont supprimés et rien n'est enregistré."""
    db_router = _get_authorized_router(router_id, db, current_user)

    async with _client_for(db_router) as client:
        # Le forfait doit exister sur le routeur ; sa durée devient la limite de
        # temps de connexion de chaque ticket (sinon un ticket n'expire jamais).
        try:
            profiles = await client.get_hotspot_profiles()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Impossible de joindre le MikroTik : {e}")

        profile = next((p for p in profiles if p.get("name") == data.profile_name), None)
        if profile is None:
            raise HTTPException(status_code=400, detail="Ce forfait n'existe pas sur le routeur.")

        limit_uptime = profile.get("session-timeout")
        if limit_uptime in (None, "", "0s", "00:00:00"):
            limit_uptime = None

        codes = _generate_unique_codes(db, data.quantite)
        sem = asyncio.Semaphore(ROUTER_CONCURRENCY)

        async def _create(code: str):
            async with sem:
                await client.create_hotspot_user(
                    name=code, password=code, profile=data.profile_name, limit_uptime=limit_uptime,
                )

        results = await asyncio.gather(*[_create(c) for c in codes], return_exceptions=True)
        created = [c for c, r in zip(codes, results) if not isinstance(r, Exception)]
        errors = [r for r in results if isinstance(r, Exception)]

        if errors:
            await _remove_users_from_router(client, created)
            raise HTTPException(
                status_code=502,
                detail=(
                    f"Échec de création sur le MikroTik ({len(errors)} ticket(s) sur {len(codes)}) : "
                    f"{errors[0]}. Aucun ticket n'a été enregistré, vous pouvez réessayer."
                ),
            )

        try:
            batch = models.VoucherBatch(
                router_id=db_router.id,
                owner_id=current_user.id,
                profile_name=data.profile_name,
                prix_unitaire=data.prix_unitaire,
                quantite=data.quantite,
                validite_jours=data.validite_jours,
                limit_uptime=limit_uptime,
            )
            db.add(batch)
            db.flush()
            db.add_all([models.Voucher(batch_id=batch.id, code=c, statut="AVAILABLE") for c in codes])
            db.commit()
        except Exception:
            db.rollback()
            await _remove_users_from_router(client, created)
            raise HTTPException(
                status_code=500,
                detail="Les tickets n'ont pas pu être enregistrés. Rien n'a été créé, vous pouvez réessayer.",
            )

    db.refresh(batch)
    return batch


@router.post("/{router_id}/sync")
async def sync_vouchers(
    router_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Met à jour à la demande l'état des tickets (connexions détectées, expirations)."""
    db_router = _get_authorized_router(router_id, db, current_user)
    try:
        async with _client_for(db_router) as client:
            return await sync_router(db, db_router, client)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=502, detail=f"Impossible de joindre le MikroTik : {e}")


@router.post("/{router_id}/rate-limit")
async def set_rate_limit(
    router_id: int,
    data: schemas.RateLimitUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Applique une limite de vitesse par client à tous les forfaits "Ticket-*"."""
    db_router = _get_authorized_router(router_id, db, current_user)
    try:
        async with _client_for(db_router) as client:
            profiles = await client.get_hotspot_profiles()
            targets = [p for p in profiles if str(p.get("name", "")).startswith("Ticket-")]
            if not targets:
                raise HTTPException(status_code=400, detail="Aucun forfait \"Ticket-*\" sur ce routeur.")
            for p in targets:
                await client.update_hotspot_profile(p[".id"], {"rate-limit": data.rate_limit})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Impossible de joindre le MikroTik : {e}")
    return {"rate_limit": data.rate_limit, "forfaits": [p["name"] for p in targets]}


@router.post("/{router_id}/login-page")
async def install_login_page(
    router_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Installe la page de connexion simplifiée (un seul champ : le code du ticket).
    Remplace la page de connexion actuelle du HotSpot."""
    db_router = _get_authorized_router(router_id, db, current_user)
    try:
        async with _client_for(db_router) as client:
            await client.write_file(LOGIN_PAGE_ROUTER_FILE, load_login_page())
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Impossible d'installer la page de connexion sur le routeur : {e}",
        )
    return {"message": "Page de connexion installée."}


@router.get("/{router_id}/vouchers", response_model=list[schemas.VoucherBatchOut])
def list_voucher_batches(
    router_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.VoucherBatch)
        .filter(models.VoucherBatch.router_id == router_id, models.VoucherBatch.owner_id == current_user.id)
        .order_by(models.VoucherBatch.created_at.desc())
        .all()
    )


@router.post("/vouchers/{voucher_id}/sell", response_model=schemas.VoucherOut)
def sell_voucher(
    voucher_id: int,
    data: schemas.SaleCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    voucher = (
        db.query(models.Voucher)
        .join(models.VoucherBatch)
        .filter(models.Voucher.id == voucher_id, models.VoucherBatch.owner_id == current_user.id)
        .first()
    )
    if not voucher:
        raise HTTPException(status_code=404, detail="Voucher introuvable.")

    if voucher.statut != "AVAILABLE":
        raise HTTPException(
            status_code=400,
            detail=f"Ce voucher n'est plus disponible (statut actuel : {voucher.statut}).",
        )

    montant = data.montant if data.montant is not None else voucher.batch.prix_unitaire

    sale = models.Sale(voucher_id=voucher.id, montant=montant, vendu_par=current_user.id)
    db.add(sale)

    voucher.statut = "USED"
    voucher.used_at = datetime.utcnow()

    db.commit()
    db.refresh(voucher)
    return voucher


@router.get("/{router_id}/sales", response_model=list[schemas.SaleOut])
def list_sales(
    router_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.Sale)
        .join(models.Voucher)
        .join(models.VoucherBatch)
        .filter(models.VoucherBatch.router_id == router_id, models.VoucherBatch.owner_id == current_user.id)
        .order_by(models.Sale.vendu_le.desc())
        .all()
    )


@router.get("/vouchers/batch/{batch_id}/pdf")
def download_voucher_batch_pdf(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    batch = (
        db.query(models.VoucherBatch)
        .filter(models.VoucherBatch.id == batch_id, models.VoucherBatch.owner_id == current_user.id)
        .first()
    )
    if not batch:
        raise HTTPException(status_code=404, detail="Lot de tickets introuvable.")

    batch_router = db.query(models.Router).filter(models.Router.id == batch.router_id).first()
    wifi_ssid = batch_router.wifi_ssid if batch_router else None

    pdf_bytes = generate_vouchers_pdf(batch, batch.vouchers, wifi_ssid=wifi_ssid)

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=tickets-{batch.id}.pdf"},
    )



@router.delete("/vouchers/{voucher_id}")
async def delete_voucher(
    voucher_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Supprime un ticket non vendu (disponible ou expiré)."""
    voucher = _get_authorized_voucher(voucher_id, db, current_user)
    if voucher.statut == "USED":
        raise HTTPException(
            status_code=400,
            detail="Ce ticket a déjà été vendu : il ne peut pas être supprimé, pour garder l'historique des ventes.",
        )

    db_router = _get_authorized_router(voucher.batch.router_id, db, current_user)
    try:
        async with _client_for(db_router) as client:
            await _delete_codes_from_router(client, [voucher.code])
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Impossible de supprimer ce ticket sur le MikroTik : {e}")

    batch = voucher.batch
    db.delete(voucher)
    db.flush()

    remaining = db.query(models.Voucher).filter(models.Voucher.batch_id == batch.id).count()
    batch.quantite = remaining
    if remaining == 0:
        db.delete(batch)
    db.commit()

    return {"message": "Ticket supprimé."}


@router.delete("/vouchers/batch/{batch_id}")
async def delete_voucher_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Supprime tous les tickets non vendus d'un lot. Les tickets déjà vendus sont
    conservés (historique des ventes) ; le lot n'est retiré que s'il n'en reste aucun."""
    batch = _get_authorized_batch(batch_id, db, current_user)
    deletable = [v for v in batch.vouchers if v.statut != "USED"]
    kept = len(batch.vouchers) - len(deletable)

    if deletable:
        db_router = _get_authorized_router(batch.router_id, db, current_user)
        try:
            async with _client_for(db_router) as client:
                await _delete_codes_from_router(client, [v.code for v in deletable])
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Impossible de supprimer ces tickets sur le MikroTik : {e}")

        for v in deletable:
            db.delete(v)
        db.flush()

    remaining = db.query(models.Voucher).filter(models.Voucher.batch_id == batch.id).count()
    batch.quantite = remaining
    if remaining == 0:
        db.delete(batch)
    db.commit()

    return {"supprimes": len(deletable), "conserves_vendus": kept}