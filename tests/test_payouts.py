"""Tests de l'interprétation des réponses de décaissement PayGate (app/payouts.py).

Règle vérifiée : on ne conclut à un ÉCHEC (donc à un remboursement automatique) que si
PayGate a clairement refusé. Tout le reste est INCERTAIN, pour ne jamais payer deux fois.
Lancer avec :  python -m pytest tests/test_payouts.py
"""
from app.payouts import ECHEC, INCERTAIN, SUCCES, classify_disburse_response


def test_succes_quand_paygate_renvoie_200():
    assert classify_disburse_response(200, {"status": 200}) == SUCCES


def test_code_200_en_texte_accepte():
    assert classify_disburse_response(200, {"status": "200"}) == SUCCES


def test_refus_explicite_est_un_echec():
    assert classify_disburse_response(200, {"status": 4}) == ECHEC
    assert classify_disburse_response(400, {"status": 6}) == ECHEC


def test_aucune_reponse_est_incertain():
    # Coupure réseau ou délai dépassé : l'argent est peut-être parti.
    assert classify_disburse_response(None, None) == INCERTAIN


def test_erreur_serveur_paygate_est_incertain():
    assert classify_disburse_response(502, None) == INCERTAIN
    assert classify_disburse_response(500, {"status": 4}) == INCERTAIN


def test_reponse_illisible_est_incertain():
    assert classify_disburse_response(200, None) == INCERTAIN
    assert classify_disburse_response(200, "<html>erreur</html>") == INCERTAIN
    assert classify_disburse_response(200, {}) == INCERTAIN
    assert classify_disburse_response(200, {"status": None}) == INCERTAIN
    assert classify_disburse_response(200, {"status": True}) == INCERTAIN
    assert classify_disburse_response(200, {"status": "inconnu"}) == INCERTAIN
