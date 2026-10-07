"""Tests du client RouterOS : lecture de réponses contenant des octets binaires, et écriture
d'un fichier sans télécharger la liste complète des fichiers du routeur.
Lancer avec :  pytest tests/test_routeros_client.py
"""
import asyncio

from app.routeros_client import RouterOSClient, decode_json

PNG_HEADER = b"\x89PNG\r\n\x1a\n"


def test_reponse_avec_image_brute_lisible():
    body = b'[{".id":"*1","name":"hotspot/img/logo.png","contents":"' + PNG_HEADER + b'"},{".id":"*2","name":"hotspot/login.html"}]'
    files = decode_json(body)
    assert [f["name"] for f in files] == ["hotspot/img/logo.png", "hotspot/login.html"]


def test_reponse_vide():
    assert decode_json(b"") is None


class _FakeRouter(RouterOSClient):
    """Faux routeur : enregistre les requêtes au lieu de les envoyer."""

    def __init__(self, existing):
        super().__init__("10.10.0.5", "u", "p")
        self.existing = existing
        self.calls = []

    async def _request(self, method, path, data=None, params=None):
        self.calls.append((method, path, params, data))
        if method == "GET":
            return [f for f in self.existing if f["name"] == params["name"]]
        return {}


def test_ecriture_ne_demande_que_le_fichier_concerne():
    router = _FakeRouter([{".id": "*7", "name": "hotspot/login.html"}])
    asyncio.run(router.write_file("hotspot/login.html", "<html></html>"))
    method, path, params, _ = router.calls[0]
    assert (method, path) == ("GET", "file")
    assert params == {"name": "hotspot/login.html", ".proplist": ".id,name"}
    assert router.calls[1][:2] == ("PATCH", "file/*7")


def test_creation_si_le_fichier_n_existe_pas():
    router = _FakeRouter([])
    asyncio.run(router.write_file("hotspot/status.html", "<html></html>"))
    assert router.calls[1][:2] == ("PUT", "file")
    assert router.calls[1][3] == {"name": "hotspot/status.html", "contents": "<html></html>"}


# ---- session coupée par le routeur -----------------------------------------------
from app.routeros_client import RouterOSError


class _FlakyRouter(RouterOSClient):
    """Coupe la session à la première requête, puis répond normalement."""

    def __init__(self):
        super().__init__("10.10.0.5", "u", "p")
        self.sent = []
        self.reconnects = 0

    async def _send(self, method, path, data, params):
        self.sent.append(method)
        if len(self.sent) == 1:
            raise RouterOSError(400, "Session closed")
        return {"ok": True}

    async def _reconnect(self):
        self.reconnects += 1


def test_nouvelle_tentative_si_session_coupee():
    router = _FlakyRouter()
    assert asyncio.run(router._request("PATCH", "file/*1", {"contents": "x"})) == {"ok": True}
    assert router.sent == ["PATCH", "PATCH"] and router.reconnects == 1


def test_pas_de_nouvelle_tentative_pour_une_creation():
    router = _FlakyRouter()
    try:
        asyncio.run(router._request("PUT", "file", {"name": "a"}))
    except RouterOSError:
        pass
    else:
        raise AssertionError("l'erreur aurait dû remonter")
    assert router.sent == ["PUT"]
