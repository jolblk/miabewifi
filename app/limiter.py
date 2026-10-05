"""Limitation du nombre de requêtes (anti force brute, anti abus).

UNE SEULE instance pour toute l'application : toutes les routes l'importent d'ici.

Les compteurs sont gardés en mémoire du processus : c'est correct tant que l'API tourne avec
un seul processus uvicorn (cas actuel). Avec plusieurs processus ou serveurs, il faudra un
stockage partagé (Redis), sinon chaque processus compterait de son côté.
"""
import ipaddress

from fastapi import Request
from slowapi import Limiter


def _is_private(ip: str) -> bool:
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return address.is_private or address.is_loopback


def client_ip(request: Request) -> str:
    """Adresse IP réelle du visiteur.

    Derrière notre reverse proxy, toutes les requêtes semblent venir du proxy : sans cette
    fonction, tous les visiteurs partageraient le même compteur (et 10 échecs de connexion
    bloqueraient tout le monde). Le proxy ajoute la vraie IP à la fin de X-Forwarded-For.

    On ne croit cet en-tête QUE si la requête arrive d'une adresse privée (le proxy, sur la
    même machine ou le réseau Docker). Si quelqu'un contacte l'API directement depuis
    Internet, l'en-tête est ignoré : il ne peut pas s'inventer une nouvelle IP à chaque essai.
    """
    peer = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded and _is_private(peer):
        last = forwarded.split(",")[-1].strip()
        if last:
            return last
    return peer


limiter = Limiter(key_func=client_ip)