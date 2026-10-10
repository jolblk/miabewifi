"""Réglages de la plateforme modifiables depuis l'administration.

Aujourd'hui : le pourcentage de frais prélevé sur chaque retrait du portefeuille. Ces frais
couvrent les frais PayGate (encaissement d'une recharge + décaissement d'un retrait) : sans eux,
recharger puis retirer aussitôt ferait payer ces frais à MIABEWIFI à chaque aller-retour.
"""
from decimal import Decimal, InvalidOperation

from app import models
from app.fees import compute_sale_split

WITHDRAWAL_FEE_KEY = "frais_retrait_pourcent"
DEFAULT_WITHDRAWAL_FEE_PERCENT = Decimal("2")
MAX_WITHDRAWAL_FEE_PERCENT = Decimal("20")


def parse_fee_percent(value) -> Decimal:
    """Pourcentage valide (0 à 20, deux décimales au plus) ou ValueError."""
    try:
        percent = Decimal(str(value).strip().replace(",", "."))
    except (InvalidOperation, AttributeError):
        raise ValueError("Pourcentage invalide.")
    if not percent.is_finite() or percent < 0 or percent > MAX_WITHDRAWAL_FEE_PERCENT:
        raise ValueError(f"Le pourcentage doit être compris entre 0 et {MAX_WITHDRAWAL_FEE_PERCENT}.")
    if percent != percent.quantize(Decimal("0.01")):
        raise ValueError("Deux chiffres après la virgule au maximum.")
    return percent.quantize(Decimal("0.01")).normalize()


def get_withdrawal_fee_percent(db) -> Decimal:
    row = db.query(models.PlatformSetting).filter(models.PlatformSetting.key == WITHDRAWAL_FEE_KEY).first()
    if row is None:
        return DEFAULT_WITHDRAWAL_FEE_PERCENT
    try:
        return parse_fee_percent(row.value)
    except ValueError:
        return DEFAULT_WITHDRAWAL_FEE_PERCENT  # valeur abîmée : jamais 0 % par accident


def set_withdrawal_fee_percent(db, value, admin_email: str | None = None) -> Decimal:
    percent = parse_fee_percent(value)
    row = db.query(models.PlatformSetting).filter(models.PlatformSetting.key == WITHDRAWAL_FEE_KEY).first()
    if row is None:
        row = models.PlatformSetting(key=WITHDRAWAL_FEE_KEY, value=format(percent, "f"))
        db.add(row)
    row.value = format(percent, "f")
    row.updated_by = admin_email
    db.commit()
    return percent


def withdrawal_split(montant: int, percent: Decimal) -> tuple[int, int]:
    """(frais, montant reçu) pour un retrait de `montant` FCFA. Frais arrondis au franc supérieur."""
    return compute_sale_split(montant, Decimal(percent) / 100)


def percent_as_number(percent: Decimal):
    """2 -> 2 ; 1.5 -> 1.5 (pour le JSON)."""
    return int(percent) if percent == percent.to_integral_value() else float(percent)
