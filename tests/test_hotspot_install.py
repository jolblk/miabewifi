"""Tests de l'installation des pages HotSpot quand l'écriture directe échoue
(app/mikrotik_scripts.py : install_hotspot_pages).
Lancer avec :  pytest tests/test_hotspot_install.py
(variables d'environnement requises par app.config : DATABASE_URL, CRYPT_KEY, SERVER_PUBLIC_KEY)
"""
import asyncio
from types import SimpleNamespace

from app import mikrotik_scripts as m


def _router():
    return SimpleNamespace(public_token="tok123", brand_name=None, brand_color=None, brand_logo=None,
                           brand_slogan=None, brand_phone=None, brand_background_version=None)


class _Client:
    def __init__(self, write_fails=(), fetch_fails=False):
        self.write_fails = set(write_fails)
        self.fetch_fails = fetch_fails
        self.written, self.fetched = [], []

    async def get(self, path):
        return []

    async def write_file(self, name, contents):
        if name in self.write_fails:
            raise RuntimeError("400 Session closed")
        self.written.append(name)

    async def fetch_file(self, url, dst_path):
        if self.fetch_fails:
            raise RuntimeError("fetch refusé")
        self.fetched.append((url, dst_path))


def test_secours_par_telechargement():
    client = _Client(write_fails={"hotspot/login.html"})
    written = asyncio.run(m.install_hotspot_pages(client, _router()))
    assert len(written) == 4
    assert client.fetched == [(m.hotspot_page_url("tok123", "login.html"), "hotspot/login.html")]
    assert "hotspot/status.html" in client.written


def test_message_precis_si_tout_echoue():
    client = _Client(write_fails={"hotspot/status.html"}, fetch_fails=True)
    try:
        asyncio.run(m.install_hotspot_pages(client, _router()))
    except RuntimeError as e:
        assert "hotspot/status.html" in str(e) and "Session closed" in str(e) and "fetch refusé" in str(e)
    else:
        raise AssertionError("l'erreur aurait dû remonter")
