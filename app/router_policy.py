"""Règles d'ajout d'un routeur : essai gratuit et limite anti-abus.

Module sans dépendance (ni base de données, ni FastAPI) pour pouvoir être testé isolément.

Pourquoi ces règles : chaque routeur occupe une adresse du tunnel WireGuard, et ces adresses
sont en nombre limité pour TOUTE la plateforme. Sans limite, un seul compte pourrait créer des
centaines de routeurs gratuits et bloquer les inscriptions de tout le monde, ou supprimer et
recréer son routeur pour obtenir un essai gratuit sans fin.
"""

TRIAL_DAYS = 3

# Nombre maximum de routeurs n'ayant JAMAIS eu de forfait payé, par compte. La marge de 2
# permet de recommencer une installation ratée sans devoir supprimer le premier routeur.
MAX_UNPAID_ROUTERS = 2

# Une alerte est envoyée aux administrateurs quand il reste ce nombre d'adresses ou moins.
LOW_IP_ALERT_THRESHOLD = 20


class RouterLimitReached(Exception):
    pass


def decide_router_creation(is_admin: bool, trial_used: bool, unpaid_routers: int) -> bool:
    """Décide si le compte peut ajouter un routeur, et s'il reçoit l'essai gratuit.

    Renvoie True si l'essai gratuit doit être accordé, False sinon.
    Lève RouterLimitReached si le compte a déjà trop de routeurs jamais payés.
    Les administrateurs n'ont pas de limite (tests, dépannage) mais une seule fois l'essai.
    """
    if not is_admin and unpaid_routers >= MAX_UNPAID_ROUTERS:
        raise RouterLimitReached()
    return not trial_used