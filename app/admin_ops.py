"""Règles des actions d'administration : abonnements offerts, corrections de solde.
Fonctions sans base de données ni FastAPI, pour pouvoir être testées seules.
"""
from datetime import datetime, timedelta

# Méthodes enregistrées sur les opérations d'abonnement (colonne transactions.methode).
METHODE_PAYE = "PACK"
METHODE_OFFERT = "OFFERT"
METHODE_ARRET = "ARRET"

MAX_JOURS_OFFERTS = 3650


def subscription_kind(router, last_pack_methode: str | None, now: datetime) -> str:
    """« offert », « abonnement », « essai », « expire » ou « aucun »."""
    if router.subscription_expires_at and router.subscription_expires_at > now:
        return "offert" if last_pack_methode == METHODE_OFFERT else "abonnement"
    if router.trial_expires_at and router.trial_expires_at > now:
        return "essai"
    if router.subscription_expires_at or router.trial_expires_at:
        return "expire"
    return "aucun"


def extended_expiry(current: datetime | None, now: datetime, jours: int) -> datetime:
    """Ajoute `jours` à l'abonnement en cours, ou part d'aujourd'hui s'il n'y en a pas."""
    if not 1 <= jours <= MAX_JOURS_OFFERTS:
        raise ValueError("Durée invalide.")
    base = current if current and current > now else now
    return base + timedelta(days=jours)


def check_adjustment(solde: int, montant: int, motif: str | None) -> None:
    """Une correction de solde doit avoir un motif et ne jamais rendre le solde négatif."""
    if not montant:
        raise ValueError("Indiquez un montant différent de zéro.")
    if not motif or len(motif.strip()) < 3:
        raise ValueError("Indiquez le motif de la correction.")
    if solde + montant < 0:
        raise ValueError("Le solde ne peut pas devenir négatif.")
