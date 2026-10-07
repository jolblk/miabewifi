"""Présentation de l'historique du portefeuille : libellés en français, numéros masqués,
bilan du mois. Fonctions sans base de données ni FastAPI, pour pouvoir être testées seules.
"""
from datetime import datetime

TYPE_LABELS = {
    "vente": "Vente en ligne",
    "recharge": "Recharge",
    "retrait": "Retrait",
    "debit": "Abonnement",
}

NETWORK_LABELS = {"FLOOZ": "Flooz", "TMONEY": "T-Money"}

STATUS_LABELS = {
    ("retrait", "confirme"): "Envoyé",
    ("retrait", "a_verifier"): "En vérification",
    ("retrait", "echoue"): "Échoué, montant rendu",
    ("retrait", "en_attente"): "En cours",
    ("recharge", "confirme"): "Confirmée",
    ("recharge", "en_attente"): "En attente de validation",
    ("recharge", "echoue"): "Échouée",
}


def mask_phone(phone: str | None) -> str:
    """« 90123412 » -> « 90 •• •• 12 » ; garde l'indicatif s'il y en a un."""
    if not phone:
        return ""
    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    if len(digits) < 6:
        return "•" * len(digits)
    local = digits[-8:] if len(digits) >= 8 else digits
    return f"{local[:2]} •• •• {local[-2:]}"


def network_label(methode: str | None) -> str:
    return NETWORK_LABELS.get((methode or "").upper(), methode or "")


def signed_amount(tx_type: str, montant: int) -> int:
    """Montant vu du solde : positif s'il entre, négatif s'il sort."""
    return montant if tx_type in ("vente", "recharge") else -montant


def counts_in_balance(tx_type: str, statut: str) -> bool:
    """L'opération a-t-elle réellement modifié le solde ?
    Un retrait « a_verifier » a bien été retiré du solde (montant réservé)."""
    if tx_type == "retrait":
        return statut in ("confirme", "a_verifier", "en_attente")
    return statut == "confirme"


def describe(tx, *, sale=None, purchase=None, forfait: str | None = None, router_name: str | None = None) -> dict:
    """Une ligne d'historique lisible. `tx` : la transaction ; `sale`/`purchase`/`forfait` :
    le détail d'une vente en ligne ; `router_name` : le routeur d'un abonnement."""
    tx_type = tx.type or "recharge"
    titre = TYPE_LABELS.get(tx_type, tx_type)
    detail = ""
    if tx_type == "vente":
        if forfait:
            titre = f"Vente en ligne · {forfait}"
        parts = []
        phone = getattr(purchase, "telephone", None) or getattr(sale, "acheteur_telephone", None)
        if phone:
            parts.append(f"{network_label(tx.methode)} {mask_phone(phone)}".strip())
        frais = getattr(sale, "frais", None)
        if frais:
            parts.append(f"frais {frais} F")
        detail = " · ".join(parts)
    elif tx_type == "retrait":
        phone = getattr(tx, "telephone", None)
        titre = f"Retrait vers {network_label(tx.methode)}" + (f" {mask_phone(phone)}" if phone else "")
        detail = STATUS_LABELS.get((tx_type, tx.statut), "")
    elif tx_type == "recharge":
        phone = getattr(tx, "telephone", None)
        titre = f"Recharge {network_label(tx.methode)}".strip()
        detail = " · ".join(p for p in [mask_phone(phone), STATUS_LABELS.get((tx_type, tx.statut), "")] if p)
    elif tx_type == "debit":
        titre = "Abonnement" + (f" · {router_name}" if router_name else "")
    return {
        "id": tx.id,
        "type": tx_type,
        "statut": tx.statut,
        "titre": titre,
        "detail": detail,
        "montant": tx.montant,
        "montant_signe": signed_amount(tx_type, tx.montant),
        "frais": getattr(sale, "frais", None) if tx_type == "vente" else None,
        "created_at": tx.created_at,
    }


def month_bounds(month: str | None, now: datetime | None = None) -> tuple[datetime, datetime]:
    """« 2026-10 » -> (1er octobre 00:00, 1er novembre 00:00). Vide : le mois en cours."""
    now = now or datetime.utcnow()
    if month:
        year, mon = (int(x) for x in month.split("-", 1))
    else:
        year, mon = now.year, now.month
    if not 1 <= mon <= 12 or not 2000 <= year <= 2100:
        raise ValueError("Mois invalide.")
    start = datetime(year, mon, 1)
    end = datetime(year + 1, 1, 1) if mon == 12 else datetime(year, mon + 1, 1)
    return start, end


def month_summary(rows) -> dict:
    """Bilan à partir de tuples (type, statut, montant, frais_de_la_vente_ou_None)."""
    summary = {"ventes": 0, "frais": 0, "recharges": 0, "abonnements": 0, "retraits": 0}
    for tx_type, statut, montant, frais in rows:
        if not counts_in_balance(tx_type, statut):
            continue
        if tx_type == "vente":
            summary["ventes"] += montant + (frais or 0)
            summary["frais"] += frais or 0
        elif tx_type == "recharge":
            summary["recharges"] += montant
        elif tx_type == "debit":
            summary["abonnements"] += montant
        elif tx_type == "retrait":
            summary["retraits"] += montant
    summary["net"] = summary["ventes"] - summary["frais"] + summary["recharges"] - summary["abonnements"] - summary["retraits"]
    return summary
