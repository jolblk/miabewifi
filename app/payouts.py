"""Interprétation de la réponse de PayGate à une demande de décaissement
(retrait du portefeuille, remboursement d'un ticket épuisé).

Module volontairement sans dépendance (ni base de données, ni FastAPI, ni httpx) pour
pouvoir être testé isolément.

Règle de prudence : un décaissement n'est considéré comme ÉCHOUÉ que si PayGate a
répondu clairement qu'il le refusait. Une coupure réseau, un délai dépassé, une erreur
serveur ou une réponse illisible ne prouvent PAS que l'argent n'est pas parti : le
résultat est alors « incertain ». Dans ce cas on ne rembourse JAMAIS automatiquement
(sinon le client risque d'être payé deux fois) : les fonds restent bloqués jusqu'à ce
qu'un administrateur vérifie dans le tableau de bord PayGate.
"""

SUCCES = "succes"
ECHEC = "echec"
INCERTAIN = "incertain"

# Code renvoyé par PayGate (/api/v1/disburse) quand le décaissement est accepté.
PAYGATE_DISBURSE_OK = 200


def classify_disburse_response(http_status, body) -> str:
    """Classe la réponse de PayGate en SUCCES, ECHEC ou INCERTAIN.

    http_status : code HTTP de la réponse, ou None si aucune réponse n'a été reçue
                  (coupure réseau, délai dépassé...).
    body        : contenu JSON déjà décodé, ou None s'il était illisible.
    """
    if http_status is None:
        return INCERTAIN  # aucune réponse : impossible de savoir si l'argent est parti
    if http_status >= 500:
        return INCERTAIN  # PayGate en panne pendant le traitement : issue inconnue
    if not isinstance(body, dict):
        return INCERTAIN  # réponse illisible

    status = body.get("status")
    if isinstance(status, bool):
        return INCERTAIN
    if isinstance(status, str) and status.strip().isdigit():
        status = int(status.strip())
    if not isinstance(status, int):
        return INCERTAIN  # pas de code exploitable dans la réponse

    if status == PAYGATE_DISBURSE_OK:
        return SUCCES
    return ECHEC  # PayGate a répondu clairement avec un code de refus
