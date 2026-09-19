from fastapi.testclient import TestClient
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import limiter as app_limiter


def test_app_limiter_is_configured():
    # L'instance Limiter utilisée par l'application doit être celle partagée par app.limiter.
    assert isinstance(app_limiter, Limiter)
    assert app_limiter.key_func is get_remote_address
