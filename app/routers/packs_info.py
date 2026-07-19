from fastapi import APIRouter
from app.packs import PACKS

router = APIRouter(prefix="/packs", tags=["Packs"])


@router.get("/")
def list_packs():
    return [{"id": k, **v} for k, v in PACKS.items()]