import os
from dotenv import load_dotenv

from cryptography.fernet import Fernet

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

SERVER_PUBLIC_KEY = os.getenv("SERVER_PUBLIC_KEY")
SERVER_ENDPOINT = os.getenv("SERVER_ENDPOINT")

CRYPT_KEY = os.getenv("CRYPT_KEY")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL manquant dans le fichier .env")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY manquant dans le fichier .env")
if not CRYPT_KEY:
    raise ValueError(
        "CRYPT_KEY manquant dans le fichier .env (clé de chiffrement des identifiants MikroTik)"
    )

fernet = Fernet(CRYPT_KEY.encode())
