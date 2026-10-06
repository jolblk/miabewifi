"""Prix et options de vente de chaque forfait HotSpot (un réglage par forfait et par routeur).

Ils pré-remplissent la création de tickets : l'agent choisit un forfait, le prix suit.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.dependencies import get_current_user
from app.models_forfaits import ForfaitSetting
from app.routers.hotspot import _get_authorized_router

router = APIRouter(prefix="/hotspot", tags=["hotspot"])

PROFILE_NAME_PATH = Path(min_length=1, max_length=60)


class ForfaitSettingIn(BaseModel):
    prix: int = Field(gt=0, le=1_000_000)
    validite_jours: Optional[int] = Field(default=None, ge=1, le=365)
    quota_mo: Optional[int] = Field(default=None, ge=1, le=1_000_000)


class ForfaitSettingOut(BaseModel):
    profile_name: str
    prix: int
    validite_jours: Optional[int] = None
    quota_mo: Optional[int] = None

    class Config:
        from_attributes = True


@router.get("/{router_id}/forfait-settings", response_model=list[ForfaitSettingOut])
def list_forfait_settings(
    router_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_router = _get_authorized_router(router_id, db, current_user)
    return (
        db.query(ForfaitSetting)
        .filter(ForfaitSetting.router_id == db_router.id)
        .order_by(ForfaitSetting.prix.asc())
        .all()
    )


@router.put("/{router_id}/forfait-settings/{profile_name}", response_model=ForfaitSettingOut)
def save_forfait_setting(
    router_id: int,
    data: ForfaitSettingIn,
    profile_name: str = PROFILE_NAME_PATH,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Crée ou met à jour le prix (et les options) d'un forfait de ce routeur."""
    db_router = _get_authorized_router(router_id, db, current_user)
    setting = (
        db.query(ForfaitSetting)
        .filter(ForfaitSetting.router_id == db_router.id, ForfaitSetting.profile_name == profile_name)
        .first()
    )
    if setting is None:
        setting = ForfaitSetting(router_id=db_router.id, profile_name=profile_name)
        db.add(setting)
    setting.prix = data.prix
    setting.validite_jours = data.validite_jours
    setting.quota_mo = data.quota_mo
    db.commit()
    db.refresh(setting)
    return setting


@router.delete("/{router_id}/forfait-settings/{profile_name}")
def delete_forfait_setting(
    router_id: int,
    profile_name: str = PROFILE_NAME_PATH,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_router = _get_authorized_router(router_id, db, current_user)
    deleted = (
        db.query(ForfaitSetting)
        .filter(ForfaitSetting.router_id == db_router.id, ForfaitSetting.profile_name == profile_name)
        .delete()
    )
    db.commit()
    if not deleted:
        raise HTTPException(status_code=404, detail="Aucun prix enregistré pour ce forfait.")
    return {"message": "Prix supprimé."}
