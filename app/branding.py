"""Personnalisation d'un HotSpot par son propriétaire : nom, couleur, logo, format des codes.

Tout ce qui est validé ici est ensuite injecté dans la page de connexion du routeur et dans
le PDF des tickets : on n'accepte donc que des valeurs sûres (pas de HTML, pas de script,
images ré-encodées).
"""
import base64
import hashlib
import io
import re
import secrets
import string

from PIL import Image, UnidentifiedImageError

DEFAULT_BRAND_COLOR = "#7c3aed"  # violet MIABEWIFI

BRAND_NAME_MAX = 40
_BRAND_NAME_ALLOWED = re.compile(r"^[\w .'&!-]+$")
_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

LOGO_MAX_UPLOAD_BYTES = 2 * 1024 * 1024  # fichier envoyé (avant réduction)
LOGO_MAX_SIDE = 256                      # px, après réduction
LOGO_MAX_STORED_BYTES = 150 * 1024       # taille finale stockée (PNG)

CODE_PREFIX_MAX = 6
CODE_LENGTH_MIN = 6
CODE_LENGTH_MAX = 12
CODE_LENGTH_DEFAULT = 8
# Des codes uniquement numériques ont beaucoup moins de combinaisons : on exige plus de chiffres
# pour qu'un inconnu ne puisse pas deviner un ticket valide par essais successifs.
CODE_DIGITS_MIN_LENGTH = 8
_CODE_PREFIX_RE = re.compile(r"^[A-Z0-9]{0,%d}$" % CODE_PREFIX_MAX)


class BrandingError(ValueError):
    """Valeur de personnalisation refusée (message lisible par le client)."""


# --- Nom ---------------------------------------------------------------------

def clean_brand_name(value: str | None) -> str | None:
    """Nom affiché sur la page de connexion et les tickets. Vide -> None."""
    if value is None:
        return None
    text = " ".join(value.split())
    if not text:
        return None
    if len(text) > BRAND_NAME_MAX:
        raise BrandingError(f"Le nom est limité à {BRAND_NAME_MAX} caractères.")
    if not _BRAND_NAME_ALLOWED.match(text) or "_" in text:
        raise BrandingError("Le nom ne peut contenir que des lettres, chiffres, espaces et . ' & ! -")
    try:
        text.encode("latin-1")  # police standard du PDF
    except UnicodeEncodeError:
        raise BrandingError("Le nom contient un caractère non pris en charge sur les tickets PDF.")
    return text


# --- Couleur -----------------------------------------------------------------

def _luminance(color: str) -> float:
    channels = []
    for i in (1, 3, 5):
        c = int(color[i:i + 2], 16) / 255
        channels.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast_with_white(color: str) -> float:
    return 1.05 / (_luminance(color) + 0.05)


def clean_brand_color(value: str | None) -> str | None:
    """Couleur principale (#RRGGBB). Vide -> None. Refuse une couleur trop claire :
    le texte des boutons est blanc, il deviendrait illisible."""
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    if not _COLOR_RE.match(text):
        raise BrandingError("Couleur invalide (format attendu : #7c3aed).")
    text = text.lower()
    if contrast_with_white(text) < 3.0:
        raise BrandingError("Cette couleur est trop claire : le texte blanc des boutons serait illisible. Choisissez une couleur plus foncée.")
    return text


# --- Logo --------------------------------------------------------------------

def process_logo(raw: bytes) -> str:
    """Valide une image envoyée par le client et la convertit en petit PNG (data URI).

    Refuse tout ce qui n'est pas une vraie image PNG/JPEG ; l'image est ré-encodée
    (les métadonnées et tout contenu caché disparaissent) et réduite à 256 px.
    """
    if not raw:
        raise BrandingError("Fichier vide.")
    if len(raw) > LOGO_MAX_UPLOAD_BYTES:
        raise BrandingError("Image trop lourde (2 Mo maximum).")
    try:
        with Image.open(io.BytesIO(raw)) as probe:
            if probe.format not in ("PNG", "JPEG"):
                raise BrandingError("Format non pris en charge : utilisez une image PNG ou JPEG.")
            image = probe.convert("RGBA")
    except BrandingError:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise BrandingError("Ce fichier n'est pas une image valide (PNG ou JPEG).")

    image.thumbnail((LOGO_MAX_SIDE, LOGO_MAX_SIDE))
    out = io.BytesIO()
    image.save(out, format="PNG", optimize=True)
    data = out.getvalue()
    if len(data) > LOGO_MAX_STORED_BYTES:
        raise BrandingError("Image trop complexe : utilisez un logo plus simple.")
    return "data:image/png;base64," + base64.b64encode(data).decode("ascii")


def logo_bytes(data_uri: str | None) -> bytes | None:
    """Octets PNG d'un logo stocké, ou None."""
    if not data_uri or not data_uri.startswith("data:image/png;base64,"):
        return None
    try:
        return base64.b64decode(data_uri.split(",", 1)[1])
    except Exception:
        return None


# --- Format des codes --------------------------------------------------------

def clean_code_prefix(value: str | None) -> str | None:
    """Préfixe des codes (A-Z, 0-9, 6 max), mis en majuscules. Vide -> None."""
    if value is None:
        return None
    text = value.strip().upper()
    if not text:
        return None
    if not _CODE_PREFIX_RE.match(text):
        raise BrandingError(f"Le préfixe ne peut contenir que des lettres et chiffres ({CODE_PREFIX_MAX} maximum).")
    return text


def check_code_format(length: int, digits_only: bool) -> None:
    if not CODE_LENGTH_MIN <= length <= CODE_LENGTH_MAX:
        raise BrandingError(f"La longueur du code doit être comprise entre {CODE_LENGTH_MIN} et {CODE_LENGTH_MAX}.")
    if digits_only and length < CODE_DIGITS_MIN_LENGTH:
        raise BrandingError(
            f"Un code composé uniquement de chiffres doit en contenir au moins {CODE_DIGITS_MIN_LENGTH} "
            "(sinon il serait trop facile à deviner)."
        )


def generate_code(prefix: str | None = None, length: int = CODE_LENGTH_DEFAULT, digits_only: bool = False) -> str:
    """Un code de ticket : préfixe + `length` caractères aléatoires.
    Par défaut (8, sans préfixe) : identique à l'ancien format, ex. « A1B2C3D4 »."""
    if digits_only:
        body = "".join(secrets.choice(string.digits) for _ in range(length))
    else:
        body = secrets.token_hex((length + 1) // 2).upper()[:length]
    return (prefix or "") + body

# --- Slogan et téléphone de contact (page de connexion) ------------------------

BRAND_SLOGAN_MAX = 60
# Lettres (accents compris), chiffres, espaces et ponctuation courante. Ni « $ » (variables
# MikroTik), ni < > " (HTML) : rien qui puisse être interprété par le routeur ou le navigateur.
_BRAND_SLOGAN_ALLOWED = re.compile(r"^[\w .,'’!?&:/()+%-]+$")
_BRAND_PHONE_ALLOWED = re.compile(r"^\+?[0-9][0-9 ]{5,23}$")


def clean_brand_slogan(value: str | None) -> str | None:
    """Petite phrase sous le nom (ex : « Internet rapide et abordable »). Vide -> None."""
    if value is None:
        return None
    text = " ".join(value.split())
    if not text:
        return None
    if len(text) > BRAND_SLOGAN_MAX:
        raise BrandingError(f"Le slogan est limité à {BRAND_SLOGAN_MAX} caractères.")
    if not _BRAND_SLOGAN_ALLOWED.match(text):
        raise BrandingError("Le slogan ne peut contenir que des lettres, chiffres, espaces et la ponctuation courante.")
    return text


def clean_brand_phone(value: str | None) -> str | None:
    """Téléphone affiché pour l'aide aux clients (ex : « 90 00 00 00 »). Vide -> None."""
    if value is None:
        return None
    text = " ".join(value.split())
    if not text:
        return None
    if not _BRAND_PHONE_ALLOWED.match(text):
        raise BrandingError("Numéro de contact invalide : chiffres et espaces uniquement (ex : 90 00 00 00).")
    return text


# --- Photo de fond (page de connexion) -----------------------------------------

BACKGROUND_MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # fichier envoyé (avant réduction)
BACKGROUND_MAX_SIDE = 1280                     # px, après réduction
BACKGROUND_MAX_STORED_BYTES = 250 * 1024       # taille finale (JPEG) : rapide même sur un Wi-Fi lent


def process_background(raw: bytes) -> tuple[bytes, str]:
    """Valide une photo envoyée par le client et la convertit en JPEG léger.

    Renvoie (octets JPEG, version). La version change à chaque nouvelle photo : elle sert
    à forcer les téléphones à recharger l'image au lieu de garder l'ancienne en mémoire.
    """
    if not raw:
        raise BrandingError("Fichier vide.")
    if len(raw) > BACKGROUND_MAX_UPLOAD_BYTES:
        raise BrandingError("Photo trop lourde (8 Mo maximum).")
    try:
        with Image.open(io.BytesIO(raw)) as probe:
            if probe.format not in ("PNG", "JPEG"):
                raise BrandingError("Format non pris en charge : utilisez une photo JPEG ou PNG.")
            image = probe.convert("RGB")
    except BrandingError:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise BrandingError("Ce fichier n'est pas une image valide (JPEG ou PNG).")

    image.thumbnail((BACKGROUND_MAX_SIDE, BACKGROUND_MAX_SIDE))
    data = b""
    for quality in (75, 65, 55, 45):
        out = io.BytesIO()
        image.save(out, format="JPEG", quality=quality, optimize=True, progressive=True)
        data = out.getvalue()
        if len(data) <= BACKGROUND_MAX_STORED_BYTES:
            break
    else:
        image.thumbnail((960, 960))
        out = io.BytesIO()
        image.save(out, format="JPEG", quality=50, optimize=True, progressive=True)
        data = out.getvalue()
    version = hashlib.sha256(data).hexdigest()[:12]
    return data, version