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


def hotspot_key(request: Request) -> str:
    """Compteur pour les routes publiques de la page HotSpot : un par routeur ET par IP.

    Tous les clients d'un même Wi-Fi sortent sur Internet avec la même adresse IP (celle du
    routeur). Compter par IP seule ferait partager une seule limite à tout un hotspot : dès
    quelques clients en même temps, les paiements seraient refusés. Le jeton du routeur dans
    l'adresse sépare chaque hotspot, et les limites de ces routes sont prévues pour un hotspot
    entier (plusieurs dizaines de clients)."""
    token = request.path_params.get("token", "")
    return f"hotspot:{token}:{client_ip(request)}"


def payment_key(request: Request) -> str:
    """Compteur pour le suivi d'UN paiement (la page interroge le serveur toutes les 4 s).
    Chaque client a son propre compteur, même si tout le hotspot partage la même IP."""
    return f"paiement:{request.path_params.get('identifier', '')}"


limiter = Limiter(key_func=client_ip)