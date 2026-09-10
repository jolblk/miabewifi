import httpx
from fastapi import APIRouter, Depends, HTTPException

from app import models, schemas
from app.dependencies import get_current_user
from app.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

router = APIRouter(prefix="/support", tags=["Support"])


@router.post("/contact")
async def contacter_support(
    data: schemas.SupportMessage,
    current_user: models.User = Depends(get_current_user),
):
    if not data.message or not data.message.strip():
        raise HTTPException(status_code=400, detail="Le message ne peut pas être vide.")

    texte = (
        "🆘 Nouveau message support MIABEWIFI\n\n"
        f"👤 {current_user.nom} ({current_user.email})\n"
        f"📞 Téléphone : {data.telephone.strip() if data.telephone else 'Non précisé'}\n\n"
        f"💬 {data.message.strip()}"
    )

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise HTTPException(
            status_code=500,
            detail="Le support Telegram n'est pas configuré côté serveur.",
        )

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": texte},
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail="Impossible d'envoyer le message pour le moment. Réessaie plus tard.",
        )

    return {"message": "Message envoyé avec succès. Nous vous répondrons rapidement."}
