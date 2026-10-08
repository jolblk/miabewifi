"""Tests de l'identification du visiteur pour la limitation des requêtes (app/limiter.py).
Lancer avec :  python -m pytest tests/test_limiter.py
"""
from types import SimpleNamespace

from app.limiter import client_ip


def _request(peer, forwarded=None):
    headers = {"x-forwarded-for": forwarded} if forwarded else {}
    return SimpleNamespace(client=SimpleNamespace(host=peer), headers=headers)


def test_derriere_le_proxy_on_prend_la_vraie_ip():
    # Le proxy (adresse Docker privée) transmet la vraie IP du visiteur.
    assert client_ip(_request("172.18.0.2", "41.207.10.5")) == "41.207.10.5"


def test_on_garde_la_derniere_entree_ajoutee_par_le_proxy():
    # Le visiteur peut écrire n'importe quoi au début de l'en-tête ; seule la fin vient du proxy.
    assert client_ip(_request("127.0.0.1", "1.2.3.4, 41.207.10.5")) == "41.207.10.5"


def test_en_tete_ignore_si_la_requete_vient_directement_d_internet():
    # Sans passer par le proxy, impossible de s'inventer une IP pour contourner la limite.
    assert client_ip(_request("41.207.10.5", "9.9.9.9")) == "41.207.10.5"


def test_sans_en_tete_on_prend_l_adresse_de_connexion():
    assert client_ip(_request("41.207.10.5")) == "41.207.10.5"


def test_en_tete_vide():
    assert client_ip(_request("172.18.0.2", " ")) == "172.18.0.2"

# ---- compteurs de la page HotSpot publique ------------------------------------------------
from app.limiter import hotspot_key, payment_key


def _hotspot_request(peer, **path_params):
    return SimpleNamespace(client=SimpleNamespace(host=peer), headers={}, path_params=path_params)


def test_deux_hotspots_derriere_la_meme_ip_ont_des_compteurs_separes():
    a = hotspot_key(_hotspot_request("41.207.10.5", token="routeurA"))
    b = hotspot_key(_hotspot_request("41.207.10.5", token="routeurB"))
    assert a != b


def test_chaque_paiement_a_son_propre_compteur_meme_sur_le_meme_wifi():
    a = payment_key(_hotspot_request("41.207.10.5", token="r", identifier="miabewifi-hs-1-1"))
    b = payment_key(_hotspot_request("41.207.10.5", token="r", identifier="miabewifi-hs-1-2"))
    assert a != b
