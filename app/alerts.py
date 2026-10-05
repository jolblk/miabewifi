"""Alertes envoyées aux administrateurs sur Telegram (même bot que le support).

Meilleur effort : si Telegram n'est pas configuré ou ne répond pas, l'erreur est
seulement écrite dans les journaux. Une alerte ne doit jamais faire échouer
l'opération qui l'envoie.
"""
import logging

import httpx

from app.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger("miabewifi.alerts")


async def alert_admins(text: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Alerte non envoyée (Telegram non configuré) : %s", text)
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT_ID, "text": text},
            )
    except Exception:
        logger.exception("Alerte Telegram impossible : %s", text)

def alert_admins_sync(text: str) -> None:
    """Même chose que alert_admins, pour les routes non asynchrones (def)."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Alerte non envoyée (Telegram non configuré) : %s", text)
        return
    try:
        with httpx.Client(timeout=10) as client:
            client.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT_ID, "text": text},
            )
    except Exception:
        logger.exception("Alerte Telegram impossible : %s", text)
