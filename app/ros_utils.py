"""Petits outils autour des durées RouterOS (ex: "1d2h3m4s") et de leur affichage."""
import re

_UNITS = {"w": 604800, "d": 86400, "h": 3600, "m": 60, "s": 1}
_TOKEN = re.compile(r"(\d+)([wdhms])")
_HMS = re.compile(r"^(\d+):(\d{2}):(\d{2})$")


def parse_ros_duration(value) -> int | None:
    """Convertit une durée RouterOS en secondes. Retourne None si vide ou illisible.

    Accepte "1d2h3m4s", "30m", "0s", "00:30:00". Une durée nulle donne 0.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    hms = _HMS.match(text)
    if hms:
        h, m, s = (int(x) for x in hms.groups())
        return h * 3600 + m * 60 + s

    tokens = _TOKEN.findall(text)
    if not tokens or "".join(n + u for n, u in tokens) != text:
        return None
    return sum(int(n) * _UNITS[u] for n, u in tokens)


def format_duration_fr(seconds: int | None) -> str:
    """Affichage court en français : 3600 -> "1 h", 86400 -> "24 h", 604800 -> "7 j"."""
    if not seconds:
        return "illimitée"
    if seconds % 86400 == 0 and seconds >= 2 * 86400:
        return f"{seconds // 86400} j"
    if seconds % 3600 == 0:
        return f"{seconds // 3600} h"
    if seconds % 60 == 0:
        return f"{seconds // 60} min"
    return f"{seconds} s"


def format_quota_fr(quota_mo: int | None) -> str | None:
    """Affichage court d'un quota de données : 500 -> "500 Mo", 1024 -> "1 Go", 1536 -> "1,5 Go"."""
    if not quota_mo:
        return None
    if quota_mo < 1024:
        return f"{quota_mo} Mo"
    go = quota_mo / 1024
    text = f"{go:.1f}".rstrip("0").rstrip(".").replace(".", ",")
    return f"{text} Go"
