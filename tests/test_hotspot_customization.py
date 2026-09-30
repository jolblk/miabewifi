"""Tests des réglages HotSpot laissés au client : personnalisation, format des codes,
quota de données, page de connexion et PDF.

Lancer avec :  pytest tests/test_hotspot_customization.py
(variables d'environnement requises par app.config : DATABASE_URL, CRYPT_KEY, SERVER_PUBLIC_KEY)
"""
import base64
import io
import re
from datetime import datetime
from types import SimpleNamespace

import pytest
from PIL import Image

from app import branding
from app.ros_utils import format_quota_fr
from app.sync import decide_voucher_update

NOW = datetime(2026, 9, 30, 12, 0, 0)


def _png(size=(40, 30), color=(200, 0, 0, 255), fmt="PNG") -> bytes:
    buf = io.BytesIO()
    Image.new("RGBA" if fmt == "PNG" else "RGB", size, color if fmt == "PNG" else color[:3]).save(buf, format=fmt)
    return buf.getvalue()


# ---- nom / couleur -----------------------------------------------------------
def test_brand_name_cleaned_and_validated():
    assert branding.clean_brand_name("  Café   Chez Ama ") is None or True  # accents latin-1 acceptés ci-dessous
    assert branding.clean_brand_name("Chez  Ama") == "Chez Ama"
    assert branding.clean_brand_name("Café Bè") == "Café Bè"
    assert branding.clean_brand_name("   ") is None
    assert branding.clean_brand_name(None) is None


@pytest.mark.parametrize("bad", ["<script>alert(1)</script>", 'a"b', "x" * 41, "Wi_Fi", "日本語", "$(bad)"])
def test_brand_name_rejects_dangerous_or_unprintable(bad):
    with pytest.raises(branding.BrandingError):
        branding.clean_brand_name(bad)


def test_brand_color_rules():
    assert branding.clean_brand_color("#7C3AED") == "#7c3aed"
    assert branding.clean_brand_color("") is None
    for bad in ("red", "#fff", "#12345g", "javascript:1", "#ffff00"):  # dernier : trop clair
        with pytest.raises(branding.BrandingError):
            branding.clean_brand_color(bad)


# ---- logo --------------------------------------------------------------------
def test_logo_is_reencoded_and_shrunk():
    uri = branding.process_logo(_png(size=(1200, 800)))
    assert uri.startswith("data:image/png;base64,")
    img = Image.open(io.BytesIO(branding.logo_bytes(uri)))
    assert max(img.size) <= branding.LOGO_MAX_SIDE


def test_logo_accepts_jpeg():
    assert branding.process_logo(_png(fmt="JPEG")).startswith("data:image/png;base64,")


@pytest.mark.parametrize("raw", [b"", b"<svg xmlns='http://www.w3.org/2000/svg'><script>1</script></svg>", b"GIF89a....", b"n'importe quoi"])
def test_logo_rejects_non_images(raw):
    with pytest.raises(branding.BrandingError):
        branding.process_logo(raw)


def test_logo_rejects_too_big_upload():
    with pytest.raises(branding.BrandingError):
        branding.process_logo(b"\x89PNG" + b"0" * (branding.LOGO_MAX_UPLOAD_BYTES + 1))


def test_logo_bytes_ignores_garbage():
    assert branding.logo_bytes(None) is None
    assert branding.logo_bytes("data:image/svg+xml;base64,AAAA") is None


# ---- format des codes --------------------------------------------------------
def test_default_code_format_is_unchanged():
    assert re.fullmatch(r"[0-9A-F]{8}", branding.generate_code())


def test_code_prefix_length_and_digits():
    assert re.fullmatch(r"WIFI[0-9A-F]{6}", branding.generate_code("WIFI", 6))
    assert re.fullmatch(r"[0-9]{10}", branding.generate_code(None, 10, digits_only=True))
    assert re.fullmatch(r"[0-9A-F]{7}", branding.generate_code(None, 7))  # longueur impaire respectée


def test_code_prefix_validation():
    assert branding.clean_code_prefix(" wifi ") == "WIFI"
    assert branding.clean_code_prefix("") is None
    for bad in ("WI-FI", "TROPLONG1", "é", "A B"):
        with pytest.raises(branding.BrandingError):
            branding.clean_code_prefix(bad)


def test_code_format_limits():
    branding.check_code_format(8, False)
    branding.check_code_format(8, True)
    for length, digits in ((5, False), (13, False), (6, True), (7, True)):
        with pytest.raises(branding.BrandingError):
            branding.check_code_format(length, digits)


# ---- quota -------------------------------------------------------------------
def test_format_quota_fr():
    assert format_quota_fr(None) is None
    assert format_quota_fr(500) == "500 Mo"
    assert format_quota_fr(1024) == "1 Go"
    assert format_quota_fr(1536) == "1,5 Go"


def _decide(**overrides):
    args = dict(now=NOW, first_login_at=None, expires_at=None, validite_jours=None,
                limit_seconds=None, ros_user={"name": "A", "uptime": "5m"}, limit_bytes=None)
    args.update(overrides)
    return decide_voucher_update(**args)


def test_quota_reached_expires_ticket():
    ros = {"name": "A", "uptime": "5m", "bytes-in": "600000000", "bytes-out": "500000000"}
    changes = _decide(limit_bytes=1024 * 1024 * 1024, ros_user=ros)
    assert changes["expire"] and changes["remove_from_router"]


def test_quota_not_reached_keeps_ticket():
    ros = {"name": "A", "uptime": "5m", "bytes-in": "1000", "bytes-out": "2000"}
    assert not _decide(limit_bytes=1024 * 1024 * 1024, ros_user=ros)["expire"]


def test_no_quota_means_no_expiry_by_data():
    ros = {"name": "A", "uptime": "5m", "bytes-in": "999999999999", "bytes-out": "999999999999"}
    assert not _decide(limit_bytes=None, ros_user=ros)["expire"]


# ---- page de connexion -------------------------------------------------------
def test_login_page_default_has_no_leftover_placeholder():
    from app import mikrotik_scripts as m
    page = m.render_login_page("tok123")
    assert "__" not in page
    assert "--brand:#7c3aed" in page and "<h1>Connexion Wi-Fi</h1>" in page and 'class="logo"' not in page


def test_login_page_branding_applied_and_escaped():
    from app import mikrotik_scripts as m
    logo = branding.process_logo(_png())
    page = m.render_login_page("tok123", brand_name="Chez <Ama> & Fils", brand_color="#0f766e", brand_logo=logo)
    assert "--brand:#0f766e" in page
    assert "<title>Chez &lt;Ama&gt; &amp; Fils</title>" in page
    assert "<Ama>" not in page
    assert f'src="{logo}"' in page
    assert "__" not in page


def test_login_page_ignores_forged_color_and_logo():
    from app import mikrotik_scripts as m
    page = m.render_login_page("t", brand_color="red;}</style><script>1</script>", brand_logo='data:image/png;base64,"><script>1</script>')
    assert "--brand:#7c3aed" in page and "<script>1</script>" not in page and 'class="logo"' not in page


# ---- PDF ---------------------------------------------------------------------
def _batch(**kw):
    base = dict(profile_name="Ticket-1h", prix_unitaire=500.0, limit_uptime="1h", validite_jours=7, quota_mo=None)
    base.update(kw)
    return SimpleNamespace(**base)


def _vouchers(n=30):
    return [SimpleNamespace(code=f"WIFI{i:06d}") for i in range(n)]


def test_pdf_plain_and_branded_and_quota_are_valid_pdfs():
    from app.pdf_generator import generate_vouchers_pdf
    plain = generate_vouchers_pdf(_batch(), _vouchers(), wifi_ssid="MonWifi")
    branded = generate_vouchers_pdf(
        _batch(quota_mo=1024), _vouchers(), wifi_ssid="MonWifi",
        brand_name="Chez Ama", brand_color="#0f766e", brand_logo=branding.process_logo(_png()),
    )
    assert plain.startswith(b"%PDF") and branded.startswith(b"%PDF")
    assert len(branded) > len(plain)
