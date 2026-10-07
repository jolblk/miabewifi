"""Tests des calculs du tableau de bord (app/dashboard_summary.py).
Lancer avec :  pytest tests/test_dashboard_summary.py
"""
from datetime import datetime

from app.dashboard_summary import day_bounds, is_low_stock, sales_by_router, stock_alerts

NOW = datetime(2026, 10, 7, 15, 30)


def test_bornes_des_jours():
    hier, auj, demain = day_bounds(NOW)
    assert (hier, auj, demain) == (datetime(2026, 10, 6), datetime(2026, 10, 7), datetime(2026, 10, 8))


def test_ventes_par_routeur():
    _, auj, _ = day_bounds(NOW)
    sales = [(1, 100, datetime(2026, 10, 7, 9)), (1, 300, datetime(2026, 10, 7, 14)),
             (1, 500, datetime(2026, 10, 6, 20)), (2, 1500, datetime(2026, 10, 7, 8))]
    assert sales_by_router(sales, auj) == {
        1: {"aujourdhui": 400, "tickets": 2, "hier": 500},
        2: {"aujourdhui": 1500, "tickets": 1, "hier": 0},
    }


def test_regle_du_stock_bas():
    assert is_low_stock(4, 100) and is_low_stock(10, 100) and not is_low_stock(11, 100)
    assert is_low_stock(5, 20) and not is_low_stock(0, 20)


def test_alertes_de_stock():
    groups = [
        {"router_id": 1, "forfait": "7 jours", "prix": 1500, "disponibles": 4, "total": 100, "dernier_lot": datetime(2026, 9, 1)},
        {"router_id": 1, "forfait": "1 heure", "prix": 100, "disponibles": 60, "total": 100, "dernier_lot": datetime(2026, 9, 1)},
        {"router_id": 2, "forfait": "24 heures", "prix": 300, "disponibles": 0, "total": 50, "dernier_lot": datetime(2026, 10, 1)},
        {"router_id": 2, "forfait": "3 heures", "prix": 150, "disponibles": 0, "total": 50, "dernier_lot": datetime(2026, 6, 1)},
    ]
    alerts = stock_alerts(groups, NOW)
    assert [(a["forfait"], a["niveau"]) for a in alerts] == [("24 heures", "epuise"), ("7 jours", "bas")]
