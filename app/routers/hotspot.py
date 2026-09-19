import io
import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app import models, schemas
from app.routeros_client import RouterOSClient
from app.pdf_generator import generate_vouchers_pdf

router = APIRouter(prefix="/hotspot", tags=["HotSpot"])


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
    from app.crypto import decrypt

    return RouterOSClient(
        router_ip=db_router.wireguard_ip,
        username=decrypt(db_router.mikrotik_api_username),
        password=decrypt(db_router.mikrotik_api_password),
    )


@router.get("/{router_id}/users")
async def list_hotspot_users(
    router_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_router = _get_authorized_router(router_id, db, current_user)
    client = _client_for(db_router)
    try:
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
    client = _client_for(db_router)
    try:
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
    client = _client_for(db_router)
    try:
        return await client.get_active_sessions()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Impossible de joindre le MikroTik : {e}")


def _generate_voucher_code() -> str:
    return secrets.token_hex(4).upper()  # ex: "A1B2C3D4"


@router.post("/{router_id}/vouchers", response_model=schemas.VoucherBatchOut)
async def create_voucher_batch(
    router_id: int,
    data: schemas.VoucherBatchCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_router = _get_authorized_router(router_id, db, current_user)
    client = _client_for(db_router)

    batch = models.VoucherBatch(
        router_id=db_router.id,
        owner_id=current_user.id,
        profile_name=data.profile_name,
        prix_unitaire=data.prix_unitaire,
        quantite=data.quantite,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    for _ in range(data.quantite):
        code = _generate_voucher_code()

        try:
            await client.create_hotspot_user(name=code, password=code, profile=data.profile_name)
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail=f"Échec de création sur le MikroTik : {e}",
            )

        db.add(models.Voucher(batch_id=batch.id, code=code, statut="AVAILABLE"))

    db.commit()
    db.refresh(batch)
    return batch


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

    pdf_bytes = generate_vouchers_pdf(batch, batch.vouchers)

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=tickets-{batch.id}.pdf"},
    )