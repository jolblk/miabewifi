"""Génération des scripts de configuration MikroTik (RouterOS v7).

Deux modes :
- "new"      : routeur vierge (configuration d'usine). Tunnel WireGuard + accès API
               + remodelage du réseau local + Wi-Fi ouvert + création du hotspot.
- "existing" : routeur déjà en service. Tunnel WireGuard + accès API uniquement.
               Ne touche ni au bridge, ni au DHCP, ni au NAT, ni à un hotspot existant.
"""
import html
import re
import secrets
import unicodedata
from pathlib import Path

from app.branding import DEFAULT_BRAND_COLOR
from app.config import SERVER_PUBLIC_KEY, PUBLIC_API_BASE_URL

SERVER_HOST = "195.35.48.80"  # IP publique du VPS
SERVER_PORT = "51820"         # port WireGuard du VPS
VPS_TUNNEL_IP = "10.10.0.1"   # adresse du VPS dans le tunnel

API_USERNAME = "miabewifi"
API_GROUP = "miabewifi-api"

SETUP_MODES = ("new", "existing")

# Vitesse maximale par client (téléchargement/envoi), sans quoi un seul client
# peut saturer toute la connexion. Modifiable ensuite depuis la page Tickets.
# Format RouterOS : "<envoi>/<téléchargement>", ex: "2M/2M".
DEFAULT_RATE_LIMIT = "2M/2M"

# Forfaits créés automatiquement sur le routeur (uniquement s'ils n'existent pas).
DEFAULT_TICKET_PROFILES = [
    {"name": "Ticket-1h", "session-timeout": "1h", "shared-users": "1", "rate-limit": DEFAULT_RATE_LIMIT},
    {"name": "Ticket-3h", "session-timeout": "3h", "shared-users": "1", "rate-limit": DEFAULT_RATE_LIMIT},
    {"name": "Ticket-24h", "session-timeout": "1d", "shared-users": "1", "rate-limit": DEFAULT_RATE_LIMIT},
    {"name": "Ticket-7j", "session-timeout": "7d", "shared-users": "1", "rate-limit": DEFAULT_RATE_LIMIT},
]

DEFAULT_WIFI_SSID = "MIABEWIFI"
SSID_ALLOWED = re.compile(r"[^A-Za-z0-9 ._-]")

LOGIN_PAGE_PATH = Path(__file__).parent / "templates" / "hotspot_login.html"
LOGIN_PAGE_ROUTER_FILE = "hotspot/login.html"

WALLED_GARDEN_COMMENT = "miabewifi-payment"
# Domaine seul (sans schéma), pour la règle walled-garden : ex "app.195.35.48.80.nip.io"
PUBLIC_API_HOST = PUBLIC_API_BASE_URL.split("://", 1)[-1].split("/", 1)[0]


def sanitize_ssid(value: str | None) -> str:
    """Nettoie un nom de Wi-Fi : sans accents ni caractères spéciaux (sûr dans un script RouterOS),
    32 caractères maximum. Retourne "MIABEWIFI" si rien ne reste."""
    if not value:
        return DEFAULT_WIFI_SSID
    ascii_only = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    cleaned = SSID_ALLOWED.sub("", ascii_only).strip()[:32].strip()
    return cleaned or DEFAULT_WIFI_SSID


DEFAULT_LOGIN_TITLE = "Connexion Wi-Fi"

TEMPLATES_DIR = Path(__file__).parent / "templates"

# Pages installées dans le dossier HotSpot du routeur (nom sur le routeur -> modèle ici).
#   login.html  : page de connexion (code du ticket, tarifs, paiement en ligne)
#   alogin.html : affichée juste après la connexion
#   status.html : temps restant, données consommées, déconnexion
#   logout.html : affichée après la déconnexion
HOTSPOT_PAGES = {
    "login.html": "hotspot_login.html",
    "alogin.html": "hotspot_alogin.html",
    "status.html": "hotspot_status.html",
    "logout.html": "hotspot_logout.html",
}

# Pictogramme Wi-Fi affiché quand le client n'a pas envoyé de logo.
_DEFAULT_MARK_HTML = (
    '<div class="mark"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.55a11 11 0 0 1 14.08 0"/>'
    '<path d="M1.42 9a16 16 0 0 1 21.16 0"/><path d="M8.53 16.11a6 6 0 0 1 6.95 0"/>'
    '<line x1="12" y1="20" x2="12.01" y2="20"/></svg></div>'
)


def _safe_text(value: str | None) -> str:
    """Texte saisi par le client, rendu inoffensif pour le HTML ET pour le routeur
    (MikroTik interprète tout ce qui commence par « $( » dans ses pages)."""
    return html.escape(value or "", quote=True).replace("$", "&#36;")


def _page_replacements(
    public_token: str,
    brand_name: str | None = None,
    brand_color: str | None = None,
    brand_logo: str | None = None,
    brand_slogan: str | None = None,
    brand_phone: str | None = None,
    background_version: str | None = None,
) -> dict[str, str]:
    color = brand_color if brand_color and re.fullmatch(r"#[0-9a-fA-F]{6}", brand_color) else DEFAULT_BRAND_COLOR
    if brand_logo and re.fullmatch(r"data:image/png;base64,[A-Za-z0-9+/=]+", brand_logo):
        logo_html = f'<img class="logo" src="{brand_logo}" alt="">'
    else:
        logo_html = _DEFAULT_MARK_HTML
    background_style = ""
    if public_token and background_version and re.fullmatch(r"[0-9a-f]{6,64}", background_version):
        url = f"{PUBLIC_API_BASE_URL}/public/hotspot/{public_token}/background.jpg?v={background_version}"
        background_style = f"background-image:url('{url}')"
    phone = _safe_text(brand_phone)
    contact_html = ""
    if phone:
        tel = re.sub(r"[^0-9+]", "", brand_phone or "")
        contact_html = f'<a class="contact" href="tel:{tel}">Besoin d\'aide ? Appelez le {phone}</a>'
    slogan = _safe_text(brand_slogan)
    return {
        "__API_BASE__": PUBLIC_API_BASE_URL,
        "__PUBLIC_TOKEN__": public_token or "",
        "__BRAND_NAME__": _safe_text(brand_name or DEFAULT_LOGIN_TITLE),
        "__BRAND_COLOR__": color,
        "__BRAND_LOGO_HTML__": logo_html,
        "__BRAND_SLOGAN_HTML__": f'<p class="slogan">{slogan}</p>' if slogan else "",
        "__CONTACT_HTML__": contact_html,
        "__BACKGROUND_STYLE__": background_style,
    }


def _render(template_name: str, replacements: dict[str, str]) -> str:
    page = (TEMPLATES_DIR / template_name).read_text(encoding="utf-8")
    for key, value in replacements.items():
        page = page.replace(key, value)
    return page


def render_login_page(public_token: str, **branding_values) -> str:
    """Page de connexion HotSpot, personnalisée pour CE routeur : les appels de paiement
    en libre-service qu'elle déclenche sont ainsi automatiquement rattachés à lui.
    Les réglages du client sont déjà validés à la saisie ; ils sont en plus échappés ici."""
    return _render(HOTSPOT_PAGES["login.html"], _page_replacements(public_token, **branding_values))


def render_hotspot_pages(db_router) -> dict[str, str]:
    """Toutes les pages HotSpot d'un routeur : {nom du fichier sur le routeur: contenu}."""
    replacements = _page_replacements(
        db_router.public_token,
        brand_name=db_router.brand_name,
        brand_color=db_router.brand_color,
        brand_logo=db_router.brand_logo,
        brand_slogan=db_router.brand_slogan,
        brand_phone=db_router.brand_phone,
        background_version=db_router.brand_background_version,
    )
    return {name: _render(template, replacements) for name, template in HOTSPOT_PAGES.items()}


async def hotspot_html_directories(client) -> list[str]:
    """Dossier(s) où le routeur lit ses pages HotSpot (réglage « html-directory » des profils
    utilisés par ses serveurs HotSpot). Par défaut : « hotspot »."""
    try:
        servers = await client.get("ip/hotspot")
        profiles = await client.get("ip/hotspot/profile")
    except Exception:
        return ["hotspot"]
    used = {s.get("profile") for s in servers}
    directories = sorted({
        (p.get("html-directory") or "").strip("/")
        for p in profiles
        if p.get("name") in used and (p.get("html-directory") or "").strip("/")
    })
    return directories or ["hotspot"]


def hotspot_page_url(public_token: str, name: str) -> str:
    """Adresse publique d'une page HotSpot déjà personnalisée pour ce routeur (méthode de secours)."""
    return f"{PUBLIC_API_BASE_URL}/public/hotspot/{public_token}/pages/{name}"


async def install_hotspot_pages(client, db_router) -> list[str]:
    """Écrit les pages HotSpot sur le routeur, dans le(s) dossier(s) qu'il utilise vraiment.
    Renvoie les chemins écrits. Les autres fichiers du dossier (images, etc.) ne sont pas touchés.

    Si l'écriture directe d'une page échoue (certains routeurs coupent la session), le routeur
    est invité à télécharger lui-même la page depuis notre serveur. Si les deux échouent, l'erreur
    indique la page concernée et les deux causes."""
    pages = render_hotspot_pages(db_router)
    written = []
    for directory in await hotspot_html_directories(client):
        for name, contents in pages.items():
            path = f"{directory}/{name}"
            try:
                await client.write_file(path, contents)
            except Exception as direct_error:
                if not db_router.public_token:
                    raise RuntimeError(f"{path} : {direct_error}") from direct_error
                try:
                    await client.fetch_file(hotspot_page_url(db_router.public_token, name), path)
                except Exception as fetch_error:
                    raise RuntimeError(
                        f"{path} : écriture directe impossible ({direct_error}), "
                        f"téléchargement par le routeur impossible ({fetch_error})"
                    ) from fetch_error
            written.append(path)
    return written

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

# Certificat HTTPS du routeur (utilisé par l'API REST sur www-ssl).
# Méthode classique RouterOS : une petite autorité locale (CA) signe le certificat du serveur.
# La signature prend de quelques secondes à plusieurs minutes selon le modèle : au lieu d'un
# délai fixe, chaque étape attend (jusqu'à CERT_SIGN_TIMEOUT_S secondes) que le certificat
# soit réellement signé (empreinte présente) avant de passer à la suivante.
# Chaque ligne est autonome (le terminal RouterOS ne garde pas les variables d'une ligne
# à l'autre) et peut être rejouée sans rien casser : ce qui est déjà signé est laissé tel quel.
CERT_SIGN_TIMEOUT_S = 300


def _cert_signed(name: str) -> str:
    return f'[:len [/certificate find where name={name} fingerprint~"."]]'


def _cert_sign_line(name: str, ca: str | None = None) -> str:
    sign = f"/certificate sign {name}" + (f" ca={ca}" if ca else "")
    return (
        f":if ({_cert_signed(name)} = 0) do={{ {sign}; :local n 0; "
        f":while ({_cert_signed(name)} = 0 && $n < {CERT_SIGN_TIMEOUT_S}) do={{ :delay 1s; :set n ($n + 1) }} }}\n"
    )


_CERTIFICATE = (
    ":if ([:len [/certificate find name=miabewifi-ca]] = 0) do={ /certificate add name=miabewifi-ca "
    "common-name=miabewifi-ca days-valid=3650 key-usage=key-cert-sign,crl-sign }\n"
    + _cert_sign_line("miabewifi-ca")
    + ":if ([:len [/certificate find name=miabewifi-cert]] = 0) do={ /certificate add name=miabewifi-cert "
    "common-name=miabewifi days-valid=3650 key-usage=digital-signature,key-encipherment,tls-server }\n"
    + _cert_sign_line("miabewifi-cert", ca="miabewifi-ca")
)

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

# Mot de passe du compte « admin » choisi par le client (routeur neuf uniquement). Un routeur
# d'usine n'a souvent aucun mot de passe et le Wi-Fi du HotSpot est ouvert : sans cette ligne,
# n'importe quel client du Wi-Fi pourrait prendre le contrôle du routeur.
_ADMIN_PASSWORD = """\
:do { /user set [find name=admin] password="__ADMIN_PASSWORD__" } on-error={}
"""

ADMIN_PASSWORD_ALLOWED = re.compile(r"^[A-Za-z0-9@#%*+=!.,:_-]{10,64}$")


# Routeur vierge (configuration d'usine : LAN 192.168.88.0/24 sur "bridge", WAN sur ether1).
# Chaque commande vérifie d'abord ce qui existe déjà. Le hotspot est activé EN DERNIER :
# la page du routeur peut se couper à ce moment, c'est normal.
_NETWORK_NEW = """\
:if ([:len [/interface bridge find name=bridge]] = 0) do={ /interface bridge add name=bridge }
:foreach p in=[/interface ethernet find where name!=ether1] do={ :do { /interface bridge port add bridge=bridge interface=[/interface ethernet get $p name] } on-error={} }
:if ([:len [/ip address find interface=bridge]] = 0) do={ /ip address add address=192.168.88.1/24 interface=bridge }
:if ([:len [/ip dhcp-client find]] = 0) do={ /ip dhcp-client add interface=ether1 disabled=no }
:if ([:len [/ip dhcp-server find interface=bridge]] = 0) do={ /ip pool add name=miabewifi-pool ranges=192.168.88.10-192.168.88.254; /ip dhcp-server add name=miabewifi-dhcp interface=bridge address-pool=miabewifi-pool disabled=no; /ip dhcp-server network add address=192.168.88.0/24 gateway=192.168.88.1 dns-server=192.168.88.1 }
:if ([:len [/ip firewall nat find where chain=srcnat action=masquerade]] = 0) do={ /ip firewall nat add chain=srcnat out-interface=ether1 action=masquerade comment="miabewifi-masquerade" }
/ip dns set allow-remote-requests=yes servers=8.8.8.8,1.1.1.1
"""

# FastTrack contourne les files d'attente : sans le désactiver, la limite de vitesse
# par client (rate-limit des forfaits) ne s'applique pas.
_FASTTRACK_OFF = """\
:do { /ip firewall filter disable [find where action=fasttrack-connection] } on-error={}
"""

# Wi-Fi ouvert (sans mot de passe) : c'est indispensable pour qu'un client puisse voir la
# page de connexion du HotSpot. Deux familles de routeurs existent sous RouterOS 7 :
# "wifi" (récents) et "wireless" (anciens). Chaque commande échoue sans bruit si le
# paquet correspondant n'est pas présent.
_WIFI_NEW = """\
:do { :foreach w in=[/interface wifi find] do={ :do { /interface bridge port add bridge=bridge interface=[/interface wifi get $w name] } on-error={} } } on-error={}
:do { /interface wifi set [find] configuration.mode=ap configuration.ssid="__SSID__" disabled=no } on-error={}
:do { /interface wifi set [find] security.authentication-types="" } on-error={}
:do { :foreach w in=[/interface wireless find] do={ :do { /interface bridge port add bridge=bridge interface=[/interface wireless get $w name] } on-error={} } } on-error={}
:do { /interface wireless security-profiles set [find default=yes] mode=none } on-error={}
:do { /interface wireless set [find] mode=ap-bridge ssid="__SSID__" security-profile=default disabled=no } on-error={}
"""

# Si le HotSpot existe déjà mais est désactivé, on l'active d'abord ; sinon on le crée (activé).
# La ligne de création reste la dernière du script.
_HOTSPOT_ENABLE = """\
:do { /ip hotspot enable [find name=miabewifi-hotspot] } on-error={}
:if ([:len [/ip hotspot profile find name=miabewifi-hsprof]] = 0) do={ /ip hotspot profile add name=miabewifi-hsprof hotspot-address=192.168.88.1 login-by=cookie,http-chap,http-pap }
:if ([:len [/ip hotspot find name=miabewifi-hotspot]] = 0) do={ /ip hotspot add name=miabewifi-hotspot interface=bridge address-pool=none profile=miabewifi-hsprof disabled=no }
"""


def build_config_script(
    *, mode: str, private_key: str, wireguard_ip: str, api_password: str,
    wifi_ssid: str | None = None, admin_password: str | None = None,
) -> str:
    if mode not in SETUP_MODES:
        raise ValueError(f"Mode d'installation inconnu : {mode}")
    if admin_password is not None and not ADMIN_PASSWORD_ALLOWED.match(admin_password):
        # Déjà vérifié à la saisie (schemas.RouterCreate) ; revérifié ici car il entre dans le script.
        raise ValueError("Mot de passe admin invalide.")

    parts = [_TUNNEL, _FIREWALL, _CERTIFICATE]
    parts.append(_SERVICE_NEW if mode == "new" else _SERVICE_EXISTING)
    parts.append(_API_USER)
    if mode == "new" and admin_password:
        parts.append(_ADMIN_PASSWORD)
    if mode == "new":
        # Le Wi-Fi puis le HotSpot sont activés EN DERNIER : si l'assistant est ouvert
        # depuis le Wi-Fi du routeur, la connexion peut se couper à ce moment.
        parts.extend([_NETWORK_NEW, _FASTTRACK_OFF, _WIFI_NEW, _HOTSPOT_ENABLE])

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
        "__SSID__": sanitize_ssid(wifi_ssid),
        "__ADMIN_PASSWORD__": admin_password or "",
    }
    for token, value in replacements.items():
        script = script.replace(token, value)
    return script