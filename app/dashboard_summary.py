"""Calculs du tableau de bord : ventes du jour par routeur et alertes de stock.
Fonctions sans base de données ni FastAPI, pour pouvoir être testées seules.
"""
import math
from datetime import datetime, timedelta

# Un forfait épuisé n'est signalé que s'il a été réapprovisionné récemment : un vieux forfait
# abandonné ne doit pas encombrer la liste « à faire ».
EXHAUSTED_RECENT_DAYS = 30


def is_low_stock(available: int, total: int) -> bool:
    """Même règle que la page Tickets : 5 tickets ou moins, ou 10 % du stock ou moins."""
    return 0 < available <= max(5, math.ceil(total * 0.1))


def day_bounds(now: datetime) -> tuple[datetime, datetime, datetime]:
    """(début d'hier, début d'aujourd'hui, début de demain), en heure du serveur (UTC = heure de Lomé)."""
    today = datetime(now.year, now.month, now.day)
    return today - timedelta(days=1), today, today + timedelta(days=1)


def sales_by_router(sales, today_start: datetime) -> dict:
    """`sales` : tuples (router_id, montant, vendu_le) depuis hier.
    Renvoie {router_id: {"aujourdhui": montant, "tickets": nombre, "hier": montant}}."""
    result = {}
    for router_id, montant, vendu_le in sales:
        entry = result.setdefault(router_id, {"aujourdhui": 0, "tickets": 0, "hier": 0})
        if vendu_le >= today_start:
            entry["aujourdhui"] += montant or 0
            entry["tickets"] += 1
        else:
            entry["hier"] += montant or 0
    return result


def stock_alerts(groups, now: datetime) -> list[dict]:
    """`groups` : dicts {router_id, forfait, prix, disponibles, total, dernier_lot}.
    Renvoie les forfaits en stock bas ou épuisés (récemment réapprovisionnés)."""
    alerts = []
    for g in groups:
        if is_low_stock(g["disponibles"], g["total"]):
            alerts.append({**g, "niveau": "bas"})
        elif g["disponibles"] == 0 and g["total"] > 0 and g["dernier_lot"] and now - g["dernier_lot"] <= timedelta(days=EXHAUSTED_RECENT_DAYS):
            alerts.append({**g, "niveau": "epuise"})
    alerts.sort(key=lambda a: (a["niveau"] != "epuise", a["disponibles"]))
    return alerts
