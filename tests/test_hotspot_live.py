"""Tests de la vue « En direct » (app/hotspot_live.py).
Lancer avec :  pytest tests/test_hotspot_live.py
"""
from types import SimpleNamespace

from app.hotspot_live import build_live_view, mask_phone, sale_info


def _session(code, left, uptime="10m", bin_="1000", bout="2000", sid="*1"):
    s = {".id": sid, "user": code, "address": "10.5.50.2", "mac-address": "AA:BB:CC:DD:EE:FF",
         "uptime": uptime, "bytes-in": bin_, "bytes-out": bout}
    if left is not None:
        s["session-time-left"] = left
    return s


def test_clients_relies_aux_tickets_et_tries_par_urgence():
    tickets = {"K7QM": {"forfait": "1 heure", "limite": 3600, "quota_mo": None, "vente": {"mode": "comptoir", "montant": 100}}}
    view = build_live_view(
        [_session("T9XA", "17h40m", sid="*2"), _session("K7QM", "8m", sid="*1"), _session("ADMIN", None, sid="*3")],
        [],
        tickets,
    )
    codes = [c["code"] for c in view["clients"]]
    assert codes == ["K7QM", "T9XA", "ADMIN"]          # le plus pressé d'abord, sans limite à la fin
    first = view["clients"][0]
    assert first["forfait"] == "1 heure" and first["connu"] and first["bientot_fini"]
    assert first["reste"] == 480 and first["limite"] == 3600 and first["octets"] == 3000
    assert view["clients"][1]["connu"] is False        # code absent de nos tickets
    assert view["connectes"] == 3 and view["bientot_finis"] == 1 and view["octets_total"] == 9000


def test_appareils_sans_ticket():
    hosts = [{"authorized": "true"}, {"authorized": "false"}, {"authorized": "false", "bypassed": "true"}, {}]
    assert build_live_view([], hosts, {})["sans_ticket"] == 2


def test_vente_en_ligne_numero_masque():
    sale = SimpleNamespace(vendu_par=None, montant=300, acheteur_telephone="99887747")
    assert sale_info(sale, SimpleNamespace(methode="TMONEY")) == {
        "mode": "en_ligne", "montant": 300, "reseau": "T-Money", "telephone": "99 •• •• 47",
    }
    assert sale_info(SimpleNamespace(vendu_par=4, montant=100, acheteur_telephone=None)) == {"mode": "comptoir", "montant": 100}
    assert sale_info(None) is None
    assert mask_phone("12") == ""


def test_donnees_illisibles_ne_cassent_rien():
    view = build_live_view([{"user": "X", "bytes-in": "abc", "uptime": "??"}], [], {})
    assert view["clients"][0]["octets"] == 0 and view["clients"][0]["depuis"] == 0
