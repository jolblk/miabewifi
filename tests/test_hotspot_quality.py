"""Tests des règles de tickets (durées, expiration, scripts MikroTik).

Lancer avec :  pytest tests/test_hotspot_quality.py
(variables d'environnement requises par app.config : DATABASE_URL, CRYPT_KEY, SERVER_PUBLIC_KEY)
"""
from datetime import datetime, timedelta

from app.ros_utils import format_duration_fr, parse_ros_duration
from app.sync import decide_voucher_update

NOW = datetime(2026, 9, 29, 12, 0, 0)


def test_parse_ros_duration():
    assert parse_ros_duration("1d2h3m4s") == 86400 + 7200 + 180 + 4
    assert parse_ros_duration("1w") == 604800
    assert parse_ros_duration("30m") == 1800
    assert parse_ros_duration("0s") == 0
    assert parse_ros_duration("00:30:00") == 1800
    assert parse_ros_duration("") is None
    assert parse_ros_duration(None) is None
    assert parse_ros_duration("n'importe quoi") is None


def test_format_duration_fr():
    assert format_duration_fr(3600) == "1 h"
    assert format_duration_fr(86400) == "24 h"
    assert format_duration_fr(7 * 86400) == "7 j"
    assert format_duration_fr(1800) == "30 min"
    assert format_duration_fr(None) == "illimitée"


def _decide(**overrides):
    args = dict(
        now=NOW, first_login_at=None, expires_at=None,
        validite_jours=30, limit_seconds=3600, ros_user={"name": "A", "uptime": "0s"},
    )
    args.update(overrides)
    return decide_voucher_update(**args)


def test_unused_ticket_stays_untouched():
    changes = _decide()
    assert "first_login_at" not in changes
    assert not changes["expire"]


def test_first_login_is_detected_and_validity_computed():
    changes = _decide(ros_user={"name": "A", "uptime": "10m"})
    assert changes["first_login_at"] == NOW - timedelta(minutes=10)
    assert changes["expires_at"] == NOW - timedelta(minutes=10) + timedelta(days=30)
    assert not changes["expire"]


def test_no_calendar_validity_when_not_requested():
    changes = _decide(validite_jours=None, ros_user={"name": "A", "uptime": "5m"})
    assert "expires_at" not in changes


def test_connection_time_exhausted_expires_and_removes():
    changes = _decide(first_login_at=NOW - timedelta(days=1), ros_user={"name": "A", "uptime": "1h"})
    assert changes["expire"] and changes["remove_from_router"]


def test_calendar_expiry_expires_and_removes():
    changes = _decide(
        first_login_at=NOW - timedelta(days=31),
        expires_at=NOW - timedelta(days=1),
        ros_user={"name": "A", "uptime": "5m"},
    )
    assert changes["expire"] and changes["remove_from_router"]


def test_user_missing_on_router_is_expired_without_removal():
    changes = _decide(ros_user=None)
    assert changes["expire"] and not changes["remove_from_router"]


def test_new_router_script_has_wifi_ratelimit_prereqs():
    from app import mikrotik_scripts as m

    script = m.build_config_script(
        mode="new", private_key="PK", wireguard_ip="10.10.0.5", api_password="pw", wifi_ssid="Café Bè",
    )
    assert 'ssid="Cafe Be"' in script
    assert "fasttrack-connection" in script
    assert "__" not in script
    # le HotSpot est activé en dernier
    assert script.rstrip().splitlines()[-1].startswith(":if ([:len [/ip hotspot find")

    existing = m.build_config_script(mode="existing", private_key="PK", wireguard_ip="10.10.0.5", api_password="pw")
    assert "/interface wifi" not in existing and "fasttrack" not in existing
    assert all("rate-limit" in p for p in m.DEFAULT_TICKET_PROFILES)


def test_script_builds_signed_ca_chain_and_waits_for_signing():
    from app import mikrotik_scripts as m

    for mode in ("new", "existing"):
        script = m.build_config_script(mode=mode, private_key="PK", wireguard_ip="10.10.0.5", api_password="pw")
        lines = script.splitlines()
        i_ca = next(i for i, l in enumerate(lines) if "/certificate sign miabewifi-ca" in l)
        i_leaf = next(i for i, l in enumerate(lines) if "/certificate sign miabewifi-cert ca=miabewifi-ca" in l)
        i_svc = next(i for i, l in enumerate(lines) if "/ip service set www-ssl" in l or "/ip service get" in l)
        # la CA est signée avant le certificat serveur, lui-même avant l'activation de www-ssl
        assert i_ca < i_leaf < i_svc
        # chaque signature attend la fin réelle de l'opération (pas de délai fixe)
        assert all(":while" in lines[i] and "fingerprint" in lines[i] for i in (i_ca, i_leaf))
        assert "key-usage=key-cert-sign,crl-sign" in script
        # chaque ligne reste autonome : aucune variable partagée entre deux lignes
        assert all(l.count(":local") == l.count(":local n 0") for l in lines)


def test_new_router_script_enables_existing_disabled_hotspot_before_creating():
    from app import mikrotik_scripts as m

    script = m.build_config_script(mode="new", private_key="PK", wireguard_ip="10.10.0.5", api_password="pw")
    lines = script.splitlines()
    i_enable = next(i for i, l in enumerate(lines) if l.startswith(":do { /ip hotspot enable"))
    assert i_enable < len(lines) - 1
    assert "disabled=no" in lines[-1]
