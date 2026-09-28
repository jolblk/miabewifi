"""Génération des scripts de configuration MikroTik (RouterOS v7).

Deux modes :
- "new"      : routeur vierge (configuration d'usine). Tunnel WireGuard + accès API
               + remodelage du réseau local + création du hotspot.
- "existing" : routeur déjà en service. Tunnel WireGuard + accès API uniquement.
               Ne touche ni au bridge, ni au DHCP, ni au NAT, ni à un hotspot existant.
"""
import secrets

from app.config import SERVER_PUBLIC_KEY

SERVER_HOST = "195.35.48.80"  # IP publique du VPS
SERVER_PORT = "51820"         # port WireGuard du VPS
VPS_TUNNEL_IP = "10.10.0.1"   # adresse du VPS dans le tunnel

API_USERNAME = "miabewifi"
API_GROUP = "miabewifi-api"

SETUP_MODES = ("new", "existing")

# Forfaits créés automatiquement sur le routeur (uniquement s'ils n'existent pas).
DEFAULT_TICKET_PROFILES = [
    {"name": "Ticket-1h", "session-timeout": "1h", "shared-users": "1"},
    {"name": "Ticket-3h", "session-timeout": "3h", "shared-users": "1"},
    {"name": "Ticket-24h", "session-timeout": "1d", "shared-users": "1"},
    {"name": "Ticket-7j", "session-timeout": "7d", "shared-users": "1"},
]


def generate_api_password() -> str:
    return secrets.token_urlsafe(24)  # uniquement A-Z a-z 0-9 - _ : sûr dans un script RouterOS


_TUNNEL = """\
/ip address remove [find interface=wg-miabewifi]
/interface/wireguard remove [find name=wg-miabewifi]
/interface/wireguard add name=wg-miabewifi listen-port=51820 private-key="__PRIVATE_KEY__"
/interface/wireguard/peers add interface=wg-miabewifi public-key="__SERVER_PUBLIC_KEY__" endpoint-address=__HOST__ endpoint-port=__PORT__ allowed-address=10.10.0.0/24 persistent-keepalive=25s
/ip/address add address=__WG_IP__/24 interface=wg-miabewifi
"""

# Autorise le VPS (et lui seul) à joindre le routeur à travers le tunnel,
# en tête de la chaîne input pour passer avant un éventuel "drop".
_FIREWALL = """\
/ip firewall filter remove [find comment="miabewifi-api"]
/ip firewall filter add chain=input action=accept in-interface=wg-miabewifi src-address=__VPS_IP__ comment="miabewifi-api"
:if ([:len [/ip firewall filter find]] > 1) do={ /ip firewall filter move [/ip firewall filter find comment="miabewifi-api"] destination=0 }
"""

_CERTIFICATE = """\
:if ([:len [/certificate find name=miabewifi-cert]] = 0) do={ /certificate add name=miabewifi-cert common-name=miabewifi days-valid=3650 key-usage=digital-signature,key-encipherment,tls-server; /certificate sign miabewifi-cert; :delay 5s }
"""

# Routeur vierge : on active www-ssl et on le limite au VPS.
_SERVICE_NEW = """\
/ip service set www-ssl disabled=no certificate=miabewifi-cert address=__VPS_IP__/32
"""

# Routeur en service : on ne modifie www-ssl que s'il est désactivé.
_SERVICE_EXISTING = """\
:if ([/ip service get [find name=www-ssl] disabled] = true) do={ /ip service set www-ssl disabled=no certificate=miabewifi-cert address=__VPS_IP__/32 }
"""

# Utilisateur API dédié, utilisable uniquement depuis le VPS.
# Si "rest-api" n'existe pas comme droit (RouterOS plus ancien), on retombe sur "api".
_API_USER = """\
/user remove [find name=__API_USER__]
/user group remove [find name=__API_GROUP__]
:do { /user group add name=__API_GROUP__ policy=read,write,api,rest-api,sensitive } on-error={ /user group add name=__API_GROUP__ policy=read,write,api,sensitive }
/user add name=__API_USER__ group=__API_GROUP__ password="__API_PASSWORD__" address=__VPS_IP__/32
"""

# Routeur vierge (configuration d'usine : LAN 192.168.88.0/24 sur "bridge", WAN sur ether1).
# Chaque commande vérifie d'abord ce qui existe déjà. Le hotspot est activé EN DERNIER :
# la page du routeur peut se couper à ce moment, c'est normal.
_HOTSPOT_NEW = """\
:if ([:len [/interface bridge find name=bridge]] = 0) do={ /interface bridge add name=bridge }
:foreach p in=[/interface ethernet find where name!=ether1] do={ :do { /interface bridge port add bridge=bridge interface=[/interface ethernet get $p name] } on-error={} }
:if ([:len [/ip address find interface=bridge]] = 0) do={ /ip address add address=192.168.88.1/24 interface=bridge }
:if ([:len [/ip dhcp-client find]] = 0) do={ /ip dhcp-client add interface=ether1 disabled=no }
:if ([:len [/ip dhcp-server find interface=bridge]] = 0) do={ /ip pool add name=miabewifi-pool ranges=192.168.88.10-192.168.88.254; /ip dhcp-server add name=miabewifi-dhcp interface=bridge address-pool=miabewifi-pool disabled=no; /ip dhcp-server network add address=192.168.88.0/24 gateway=192.168.88.1 dns-server=192.168.88.1 }
:if ([:len [/ip firewall nat find where chain=srcnat action=masquerade]] = 0) do={ /ip firewall nat add chain=srcnat out-interface=ether1 action=masquerade comment="miabewifi-masquerade" }
/ip dns set allow-remote-requests=yes servers=8.8.8.8,1.1.1.1
:if ([:len [/ip hotspot profile find name=miabewifi-hsprof]] = 0) do={ /ip hotspot profile add name=miabewifi-hsprof hotspot-address=192.168.88.1 login-by=cookie,http-chap,http-pap }
:if ([:len [/ip hotspot find name=miabewifi-hotspot]] = 0) do={ /ip hotspot add name=miabewifi-hotspot interface=bridge address-pool=none profile=miabewifi-hsprof disabled=no }
"""


def build_config_script(*, mode: str, private_key: str, wireguard_ip: str, api_password: str) -> str:
    if mode not in SETUP_MODES:
        raise ValueError(f"Mode d'installation inconnu : {mode}")

    parts = [_TUNNEL, _FIREWALL, _CERTIFICATE]
    parts.append(_SERVICE_NEW if mode == "new" else _SERVICE_EXISTING)
    parts.append(_API_USER)
    if mode == "new":
        parts.append(_HOTSPOT_NEW)  # toujours en dernier

    script = "".join(parts)
    replacements = {
        "__PRIVATE_KEY__": private_key,
        "__SERVER_PUBLIC_KEY__": SERVER_PUBLIC_KEY,
        "__HOST__": SERVER_HOST,
        "__PORT__": SERVER_PORT,
        "__WG_IP__": wireguard_ip,
        "__VPS_IP__": VPS_TUNNEL_IP,
        "__API_USER__": API_USERNAME,
        "__API_GROUP__": API_GROUP,
        "__API_PASSWORD__": api_password,
    }
    for token, value in replacements.items():
        script = script.replace(token, value)
    return script