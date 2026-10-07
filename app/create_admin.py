"""Crée un compte administrateur, ou met à jour son mot de passe s'il existe déjà.

Lancé sur le serveur par l'action GitHub « Créer un compte administrateur » :
    python -m app.create_admin
L'identifiant et le mot de passe sont lus dans les variables d'environnement ADMIN_LOGIN et
ADMIN_PASSWORD (rangées dans les secrets GitHub) : ils n'apparaissent jamais dans le code.
"""
import os
import sys

from app import models
from app.database import SessionLocal
from app.security import hash_password

MIN_PASSWORD_LENGTH = 8


def create_or_update_admin(db, login: str, password: str) -> str:
    login = (login or "").strip()
    if not login:
        raise ValueError("ADMIN_LOGIN est vide.")
    if len(password or "") < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Le mot de passe doit faire au moins {MIN_PASSWORD_LENGTH} caractères.")
    user = db.query(models.User).filter(models.User.email == login).first()
    if user is None:
        db.add(models.User(
            email=login,
            nom="Administrateur",
            hashed_password=hash_password(password),
            role="admin",
        ))
        action = "créé"
    else:
        user.hashed_password = hash_password(password)
        user.role = "admin"
        action = "mis à jour"
    db.commit()
    return action


def main() -> int:
    login = os.getenv("ADMIN_LOGIN", "")
    password = os.getenv("ADMIN_PASSWORD", "")
    db = SessionLocal()
    try:
        action = create_or_update_admin(db, login, password)
    except ValueError as e:
        print(f"Échec : {e}")
        return 1
    finally:
        db.close()
    print(f"Compte administrateur « {login.strip()} » {action}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
