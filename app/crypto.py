from app.config import fernet


def encrypt(value: str) -> str:
    """Chiffre une valeur texte avec la clé Fernet du serveur."""
    return fernet.encrypt(value.encode()).decode("utf-8")


def decrypt(value: str) -> str:
    """Déchiffre une valeur précédemment chiffrée."""
    return fernet.decrypt(value.encode()).decode("utf-8")
