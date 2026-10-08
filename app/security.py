import hashlib
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from app.config import SECRET_KEY

ALGORITHM = "HS256"
# « Rester connecté sur cet appareil » coché : 7 jours. Sinon : 12 heures (ordinateur partagé,
# cybercafé...). Dans les deux cas, changer son mot de passe ou « se déconnecter de tous les
# appareils » coupe immédiatement toutes les connexions (voir token_version).
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 jours
SHORT_ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12  # 12 heures
RESET_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: int, token_version: int = 0, remember: bool = True) -> str:
    minutes = ACCESS_TOKEN_EXPIRE_MINUTES if remember else SHORT_ACCESS_TOKEN_EXPIRE_MINUTES
    to_encode = {
        "sub": str(user_id),
        "ver": token_version or 0,
        "exp": datetime.utcnow() + timedelta(minutes=minutes),
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        return None
    # Un lien de réinitialisation (signé avec la même clé) ne doit jamais servir de connexion.
    if payload.get("purpose") is not None or not str(payload.get("sub", "")).isdigit():
        return None
    return payload


def token_is_current(payload: dict, user_token_version: int | None) -> bool:
    """Faux si le jeton date d'avant un changement de mot de passe ou une déconnexion de tous
    les appareils. Les jetons émis avant cette fonctionnalité n'ont pas de « ver » : ils
    valent 0, comme tous les comptes au départ."""
    return payload.get("ver", 0) == (user_token_version or 0)


def create_reset_token(user_id: int, token_version: int = 0) -> str:
    expire = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": str(user_id), "purpose": "password_reset", "ver": token_version or 0, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_reset_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("purpose") != "password_reset":
            return None
        return payload
    except Exception:
        return None


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()