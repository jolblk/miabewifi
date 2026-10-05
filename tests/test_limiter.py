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