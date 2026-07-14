import os
from dotenv import load_dotenv

load_dotenv()

PAYGATE_AUTH_TOKEN = os.getenv("PAYGATE_AUTH_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL manquant dans le fichier .env")