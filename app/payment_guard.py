"""Protection contre l'envoi répété de demandes de paiement vers un même numéro.

La page de paiement HotSpot est publique : sans cette règle, n'importe qui pourrait déclencher
en boucle des demandes Flooz / T-Money sur le téléphone d'une autre personne (harcèlement,
plaintes auprès de PayGate). On compte les demandes récentes vers ce numéro, TOUS routeurs
confondus, et on refuse au-delà des seuils ci-dessous.

Les tentatives dont PayGate a refusé le lancement (statut « echoue ») ne comptent pas : aucune
demande n'est arrivée sur le téléphone.
"""
from datetime import datetime, timedelta

# (fenêtre, nombre maximum de demandes dans cette fenêtre)
PHONE_LIMITS = (
    (timedelta(minutes=10), 3),
    (timedelta(hours=1), 6),
)

PHONE_LIMIT_MESSAGE = (
    "Plusieurs demandes de paiement ont déjà été envoyées à ce numéro. Validez celle reçue sur "
    "votre téléphone, ou réessayez dans quelques minutes."
)


def phone_request_allowed(request_times: list[datetime], now: datetime) -> bool:
    """Vrai si une nouvelle demande vers ce numéro est autorisée, d'après les dates des
    demandes déjà envoyées (au moins celles de la dernière heure)."""
    for window, maximum in PHONE_LIMITS:
        recent = sum(1 for t in request_times if t is not None and t >= now - window)
        if recent >= maximum:
            return False
    return True


def longest_window() -> timedelta:
    return max(window for window, _ in PHONE_LIMITS)
