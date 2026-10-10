"""Tests des correctifs de sécurité d'octobre 2026 : images trop grandes, mot de passe admin du
MikroTik, frais de retrait, champs limités.

Lancer avec :  pytest tests/test_security_fixes.py
"""
import io
from decimal import Decimal

import pytest
from PIL import Image
from pydantic import ValidationError

from app import branding, mikrotik_scripts, platform_settings, schemas, wallet_history


def _png(width, height, mode="1"):
    out = io.BytesIO()
    Image.new(mode, (width, height)).save(out, format="PNG")
    return out.getvalue()


@pytest.mark.parametrize("process", [branding.process_logo, branding.process_background])
def test_image_trop_grande_refusee(process):
    # Fichier de quelques Ko qui annonce 49 millions de pixels.
    with pytest.raises(branding.BrandingError):
        process(_png(7000, 7000))


def test_image_normale_acceptee():
    data, version = branding.process_background(_png(800, 600, "RGB"))
    assert data and version
    assert branding.process_logo(_png(300, 300, "RGB")).startswith("data:image/png;base64,")


def test_routeur_neuf_exige_un_mot_de_passe_admin():
    with pytest.raises(ValidationError):
        schemas.RouterCreate(nom="Boutique", mode="new")
    with pytest.raises(ValidationError):
        schemas.RouterCreate(nom="Boutique", mode="new", admin_password="court")
    with pytest.raises(ValidationError):
        schemas.RouterCreate(nom="Boutique", mode="new", admin_password='abc"def$ghij')
    assert schemas.RouterCreate(nom="Boutique", mode="new", admin_password="Bonjour2026!x")
    assert schemas.RouterCreate(nom="Boutique", mode="existing")


def test_script_routeur_neuf_change_le_mot_de_passe_admin():
    script = mikrotik_scripts.build_config_script(
        mode="new", private_key="PK", wireguard_ip="10.10.0.5", api_password="pw",
        admin_password="Bonjour2026!x",
    )
    assert '/user set [find name=admin] password="Bonjour2026!x"' in script
    existing = mikrotik_scripts.build_config_script(
        mode="existing", private_key="PK", wireguard_ip="10.10.0.5", api_password="pw",
    )
    assert "name=admin" not in existing
    with pytest.raises(ValueError):
        mikrotik_scripts.build_config_script(
            mode="new", private_key="PK", wireguard_ip="10.10.0.5", api_password="pw",
            admin_password='x" ; /system reset',
        )


def test_champs_limites():
    with pytest.raises(ValidationError):
        schemas.RouterCreate(nom="x" * 101)
    with pytest.raises(ValidationError):
        schemas.VoucherBatchCreate(profile_name="Ticket-1h", prix_unitaire=2_000_000, quantite=1)


def test_pourcentage_de_frais():
    assert platform_settings.parse_fee_percent("2") == Decimal("2")
    assert platform_settings.parse_fee_percent("2,5") == Decimal("2.5")
    assert platform_settings.parse_fee_percent(0) == Decimal("0")
    for bad in ("-1", "21", "abc", "1.234", "nan"):
        with pytest.raises(ValueError):
            platform_settings.parse_fee_percent(bad)


def test_calcul_des_frais_de_retrait():
    assert platform_settings.withdrawal_split(10000, Decimal("2")) == (200, 9800)
    assert platform_settings.withdrawal_split(9999, Decimal("2")) == (200, 9799)  # arrondi au franc supérieur
    assert platform_settings.withdrawal_split(10000, Decimal("0")) == (0, 10000)
    assert platform_settings.withdrawal_split(1, Decimal("2")) == (1, 0)  # refusé par la route (rien à envoyer)


def test_historique_affiche_les_frais_de_retrait():
    class Tx:
        id = 1
        type = "retrait"
        statut = "confirme"
        montant = 10000
        frais = 200
        methode = "TMONEY"
        telephone = "90123456"
        created_at = None
        note = None

    line = wallet_history.describe(Tx())
    assert line["frais"] == 200
    assert "reçu 9800 F" in line["detail"]
    assert line["montant_signe"] == -10000
