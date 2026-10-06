"""Tests des pages HotSpot installées sur les routeurs (connexion, après connexion, statut,
déconnexion) et des nouveaux réglages : slogan, téléphone de contact, photo de fond.

Lancer avec :  pytest tests/test_hotspot_pages.py
(variables d'environnement requises par app.config : DATABASE_URL, CRYPT_KEY, SERVER_PUBLIC_KEY)
"""
import asyncio
import io
import re
from types import SimpleNamespace

import pytest
from PIL import Image

from app import branding
from app import mikrotik_scripts as m


def _router(**kw):
    base = dict(
        public_token="tok123", brand_name="Chez Ama", brand_color="#0f766e", brand_logo=None,
        brand_slogan="Internet rapide & abordable", brand_phone="+228 90 00 00 00",
        brand_background_version="f456dc0ca192",
    )
    base.update(kw)
    return SimpleNamespace(**base)


# ---- slogan / téléphone ----------------------------------------------------------
def test_slogan_cleaned_and_limited():
    assert branding.clean_brand_slogan("  Internet  rapide ! ") == "Internet rapide !"
    assert branding.clean_brand_slogan("   ") is None
    with pytest.raises(branding.BrandingError):
        branding.clean_brand_slogan("x" * 61)


@pytest.mark.parametrize("bad", ["$(username)", "<b>gras</b>", 'a"b'])
def test_slogan_rejects_router_or_html_code(bad):
    with pytest.raises(branding.BrandingError):
        branding.clean_brand_slogan(bad)


def test_phone_rules():
    assert branding.clean_brand_phone(" +228 90  00 00 00 ") == "+228 90 00 00 00"
    assert branding.clean_brand_phone("") is None
    for bad in ["abc", "90-00-00", "$(ip)", "12"]:
        with pytest.raises(branding.BrandingError):
            branding.clean_brand_phone(bad)


# ---- photo de fond ---------------------------------------------------------------
def _photo(size=(2400, 1600), fmt="JPEG") -> bytes:
    buf = io.BytesIO()
    Image.effect_noise(size, 60).convert("RGB").save(buf, format=fmt, quality=90)
    return buf.getvalue()


def test_background_is_reencoded_small_jpeg():
    data, version = branding.process_background(_photo())
    image = Image.open(io.BytesIO(data))
    assert image.format == "JPEG"
    assert max(image.size) <= branding.BACKGROUND_MAX_SIDE
    assert len(data) <= branding.BACKGROUND_MAX_STORED_BYTES
    assert re.fullmatch(r"[0-9a-f]{12}", version)


def test_background_rejects_non_images():
    for raw in [b"", b"pas une image", b"GIF89a" + b"0" * 50]:
        with pytest.raises(branding.BrandingError):
            branding.process_background(raw)


# ---- rendu des pages -------------------------------------------------------------
def test_all_pages_rendered_without_leftover_placeholder():
    pages = m.render_hotspot_pages(_router())
    assert set(pages) == {"login.html", "alogin.html", "status.html", "logout.html"}
    for name, page in pages.items():
        assert not re.search(r"__[A-Z_]+__", page), name
        assert "--brand:#0f766e" in page, name
        assert "tok123/background.jpg?v=f456dc0ca192" in page, name
        assert 'href="tel:+22890000000"' in page, name


def test_login_page_shows_slogan_and_loads_offers():
    page = m.render_hotspot_pages(_router())["login.html"]
    assert '<p class="slogan">Internet rapide &amp; abordable</p>' in page
    assert "loadOffers();" in page and 'id="offers-section"' in page


def test_status_page_shows_session_details():
    page = m.render_hotspot_pages(_router())["status.html"]
    for variable in ["$(session-time-left)", "$(uptime)", "$(bytes-out-nice)", "$(link-logout)"]:
        assert variable in page


def test_optional_branding_absent_means_nothing_shown():
    pages = m.render_hotspot_pages(_router(brand_slogan=None, brand_phone=None, brand_background_version=None))
    for page in pages.values():
        assert 'class="contact"' not in page and "background-image" not in page
    assert 'class="slogan"' not in pages["login.html"]


def test_dangerous_text_cannot_reach_router_or_browser():
    page = m.render_login_page("t", brand_slogan="$(username)<script>", brand_phone='<img src=x>"')
    body = page.split("<body>", 1)[1].split("<script>\nvar API_BASE", 1)[0]
    assert "$(username)" not in body and "<script>" not in body and "<img src=x>" not in body


def test_forged_background_version_is_ignored():
    page = m.render_hotspot_pages(_router(brand_background_version="x');}</style><script>"))["login.html"]
    assert "background-image" not in page and "</style><script>" not in page


# ---- installation sur le routeur -------------------------------------------------
class _FakeClient:
    def __init__(self, servers, profiles):
        self.data = {"ip/hotspot": servers, "ip/hotspot/profile": profiles}
        self.files = {}

    async def get(self, path):
        return self.data[path]

    async def write_file(self, name, contents):
        self.files[name] = contents


def test_pages_written_in_directory_used_by_hotspot():
    client = _FakeClient([{"profile": "pro"}], [{"name": "pro", "html-directory": "flash/hotspot"}, {"name": "autre", "html-directory": "x"}])
    written = asyncio.run(m.install_hotspot_pages(client, _router()))
    assert sorted(written) == sorted(f"flash/hotspot/{n}" for n in m.HOTSPOT_PAGES)


def test_default_directory_when_unknown():
    client = _FakeClient([], [])
    written = asyncio.run(m.install_hotspot_pages(client, _router()))
    assert all(path.startswith("hotspot/") for path in written) and len(written) == 4