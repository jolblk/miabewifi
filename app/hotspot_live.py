"""Vue « En direct » d'un HotSpot : clients connectés en ce moment, reliés à nos tickets.

Le MikroTik donne, pour chaque connexion, le code utilisé, le temps restant et les données
échangées. On y ajoute ce que lui ne sait pas : le forfait, et comment le ticket a été vendu.
Fonctions sans base de données ni FastAPI, pour pouvoir être testées seules.
"""
from app.ros_utils import parse_ros_duration

# Sous ce temps restant, le client est signalé « Bientôt fini ».
ENDING_SOON_SECONDS = 15 * 60

NETWORK_LABELS = {"FLOOZ": "Flooz", "TMONEY": "T-Money"}


def mask_phone(phone: str | None) -> str:
    digits = "".join(ch for ch in str(phone or "") if ch.isdigit())
    if len(digits) < 6:
        return ""
    local = digits[-8:]
    return f"{local[:2]} •• •• {local[-2:]}"


def _int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def sale_info(sale, purchase=None) -> dict | None:
    """Comment le ticket a été vendu : au comptoir (par l'agent) ou en ligne (par le client)."""
    if sale is None:
        return None
    if sale.vendu_par is None:
        methode = getattr(purchase, "methode", None)
        return {
            "mode": "en_ligne",
            "montant": sale.montant,
            "reseau": NETWORK_LABELS.get(methode, methode),
            "telephone": mask_phone(sale.acheteur_telephone),
        }
    return {"mode": "comptoir", "montant": sale.montant}


def build_live_view(sessions: list[dict], hosts: list[dict], tickets: dict) -> dict:
    """`sessions` : /ip/hotspot/active du routeur ; `hosts` : /ip/hotspot/host ;
    `tickets` : {code: {"forfait", "limite", "quota_mo", "vente"}} pour les codes connus."""
    clients = []
    for s in sessions:
        code = s.get("user") or ""
        ticket = tickets.get(code)
        reste = parse_ros_duration(s.get("session-time-left"))
        limite = ticket["limite"] if ticket else None
        clients.append({
            "id": s.get(".id"),
            "code": code,
            "connu": ticket is not None,
            "forfait": ticket["forfait"] if ticket else None,
            "quota_mo": ticket["quota_mo"] if ticket else None,
            "vente": ticket["vente"] if ticket else None,
            "adresse": s.get("address"),
            "mac": s.get("mac-address"),
            "depuis": parse_ros_duration(s.get("uptime")) or 0,
            "reste": reste,
            "limite": limite,
            "octets": _int(s.get("bytes-in")) + _int(s.get("bytes-out")),
            "bientot_fini": reste is not None and reste <= ENDING_SOON_SECONDS,
        })
    # Les plus pressés d'abord : ceux dont le forfait se termine bientôt.
    clients.sort(key=lambda c: (c["reste"] is None, c["reste"] if c["reste"] is not None else 0))

    sans_ticket = sum(
        1 for h in hosts
        if str(h.get("authorized", "")).lower() != "true" and str(h.get("bypassed", "")).lower() != "true"
    )
    return {
        "clients": clients,
        "connectes": len(clients),
        "bientot_finis": sum(1 for c in clients if c["bientot_fini"]),
        "octets_total": sum(c["octets"] for c in clients),
        "sans_ticket": sans_ticket,
    }
