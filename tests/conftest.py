"""Valeurs par défaut des variables d'environnement exigées par app.config, pour que les tests
se lancent sans fichier .env (les vraies valeurs du serveur ne sont jamais nécessaires ici)."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("CRYPT_KEY", "0" * 43 + "=")
os.environ.setdefault("SERVER_PUBLIC_KEY", "test")
os.environ.setdefault("SECRET_KEY", "test-" + "x" * 40)
