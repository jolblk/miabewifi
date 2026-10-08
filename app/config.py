import os
from dotenv import load_dotenv

load_dotenv()

PAYGATE_AUTH_TOKEN = os.getenv("PAYGATE_AUTH_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8000/static")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL manquant dans le fichier .env")

CRYPT_KEY = os.getenv("CRYPT_KEY")
if not CRYPT_KEY:
    raise ValueError("CRYPT_KEY manquant dans le fichier .env")


WG_AGENT_HOST = os.getenv("WG_AGENT_HOST", "host.docker.internal")
WG_AGENT_KEY_PATH = os.getenv("WG_AGENT_KEY_PATH", "/app/wg_key")

SERVER_PUBLIC_KEY = os.getenv("SERVER_PUBLIC_KEY")
if not SERVER_PUBLIC_KEY:
    raise ValueError("SERVER_PUBLIC_KEY manquant dans le fichier .env")

TUTORIAL_VIDEO_URL = os.getenv("TUTORIAL_VIDEO_URL", "")

# Fréquence (en secondes) de la synchronisation des tickets avec les routeurs
# (détection des connexions, expiration). 0 = désactivée.
VOUCHER_SYNC_INTERVAL_SECONDS = int(os.getenv("VOUCHER_SYNC_INTERVAL_SECONDS", "300"))

FRONTEND_ORIGINS = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

# Domaine public de cette instance (prod ou staging), utilisé pour :
# - construire l'URL que la page HotSpot appelle pour le paiement en libre-service
# - générer la règle "walled garden" qui autorise le client à joindre ce domaine avant connexion
PUBLIC_API_BASE_URL = os.getenv("PUBLIC_API_BASE_URL", "https://app.195.35.48.80.nip.io")

# Frais prélevés sur chaque vente de ticket en libre-service (0.01 = 1 %).
# Couvre les frais PayGate sur les retraits par API. 0 = aucun frais.
HOTSPOT_SALE_FEE_RATE = os.getenv("HOTSPOT_SALE_FEE_RATE", "0.01")


# Fréquence (en secondes) du rattrapage des paiements de tickets dont le webhook PayGate
# n'est pas arrivé (on redemande l'état à PayGate). 0 = désactivé.
PURCHASE_RECONCILE_INTERVAL_SECONDS = int(os.getenv("PURCHASE_RECONCILE_INTERVAL_SECONDS", "30"))


# Documentation interactive de l'API (/docs, /redoc, /openapi.json). Désactivée par défaut :
# elle donne à n'importe qui la carte complète de l'API. Pour l'activer (en local ou sur
# staging), mettre ENABLE_API_DOCS=1 dans le fichier .env.
ENABLE_API_DOCS = os.getenv("ENABLE_API_DOCS", "0").strip().lower() in ("1", "true", "yes", "oui")
