from cryptography.fernet import Fernet
from app.config import CRYPT_KEY

_fernet = Fernet(CRYPT_KEY.encode())


def encrypt(value: str) -> str:
    if not value:
        return value
    return _fernet.encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    if not value:
        return value
    return _fernet.decrypt(value.encode()).decode()