from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from datetime import datetime
from typing import Literal, Optional
from urllib.parse import quote_plus

from app import branding


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    nom: str = Field(min_length=1, max_length=100)


class UserOut(BaseModel):
    id: int
    # Pas EmailStr ici : un compte administrateur peut avoir un simple identifiant (ex. « admin »).
    # L'inscription, elle, exige toujours une vraie adresse e-mail (UserCreate).
    email: str
    nom: str
    solde: int
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
    # Durée de la nouvelle connexion de CET appareil (même choix qu'à la connexion).
    remember: bool = True


class RouterCreate(BaseModel):
    nom: str
    mode: Literal["new", "existing"] = "existing"
    # Nom du Wi-Fi diffusé aux clients (mode "new" uniquement). Lettres, chiffres, espace . _ -
    wifi_ssid: Optional[str] = Field(default=None, max_length=32, pattern=r"^[A-Za-z0-9 ._-]*$")

class PortMappingOut(BaseModel):
    service_type: str
    public_port: int

    class Config:
        from_attributes = True

class RouterOut(BaseModel):
    id: int
    nom: str
    wireguard_ip: str | None
    public_key: str | None
    is_connected: bool
    created_at: datetime
    trial_expires_at: datetime | None
    subscription_expires_at: datetime | None
    mikrotik_api_username: str | None = None
    setup_mode: str | None = None
    wifi_ssid: str | None = None
    ports: list[PortMappingOut] = []

    class Config:
        from_attributes = True


class RouterConfigOut(BaseModel):
    router: RouterOut
    config_script: str

class MikrotikCredentialsUpdate(BaseModel):
    api_username: str
    api_password: str

# Numéro mobile money : chiffres uniquement, « + » facultatif devant (même règle que l'application).
PHONE_PATTERN = r"^\+?\d{8,15}$"
# Plafond de sécurité d'une opération (même valeur que les corrections de solde de l'admin).
MAX_OPERATION_FCFA = 10_000_000


class RechargeRequest(BaseModel):
    phone_number: str = Field(pattern=PHONE_PATTERN)
    network: Literal["FLOOZ", "TMONEY"]
    montant: int = Field(gt=0, le=MAX_OPERATION_FCFA)


class WithdrawRequest(BaseModel):
    phone_number: str = Field(pattern=PHONE_PATTERN)
    network: Literal["FLOOZ", "TMONEY"]
    montant: int = Field(gt=0, le=MAX_OPERATION_FCFA)
    password: str = Field(min_length=1, max_length=200)  # mot de passe du compte, pour confirmer


class SupportMessage(BaseModel):
    telephone: Optional[str] = Field(default=None, max_length=30)
    sujet: Optional[str] = Field(default=None, max_length=200)
    message: str = Field(max_length=3000)


class ActivatePackRequest(BaseModel):
    pack_id: str  # "7j", "30j", "90j"

class VoucherBatchCreate(BaseModel):
    profile_name: str
    prix_unitaire: int = Field(gt=0)
    quantite: int = Field(gt=0, le=500)
    # Nombre de jours de validité APRÈS la 1re connexion. Vide = pas de limite calendaire.
    validite_jours: Optional[int] = Field(default=None, ge=1, le=365)
    # Quota de données par ticket, en Mo (ex: 1024 = 1 Go). Vide = illimité.
    quota_mo: Optional[int] = Field(default=None, ge=1, le=1_000_000)


class SaleCreate(BaseModel):
    # Prix réellement encaissé (vide = prix du forfait). 0 autorisé : ticket offert.
    montant: Optional[int] = Field(default=None, ge=0, le=MAX_OPERATION_FCFA)


class SaleOut(BaseModel):
    id: int
    montant: int
    vendu_par: Optional[int] = None
    vendu_le: datetime
    acheteur_telephone: Optional[str] = None
    frais: Optional[int] = None

    class Config:
        from_attributes = True


class VoucherOut(BaseModel):
    id: int
    code: str
    statut: str
    created_at: datetime
    first_login_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    sale: Optional[SaleOut] = None

    class Config:
        from_attributes = True


class VoucherBatchOut(BaseModel):
    id: int
    profile_name: str
    prix_unitaire: int
    quantite: int
    created_at: datetime
    validite_jours: Optional[int] = None
    limit_uptime: Optional[str] = None
    quota_mo: Optional[int] = None
    online_sale: bool = True
    vouchers: list[VoucherOut] = []

    class Config:
        from_attributes = True


class RateLimitUpdate(BaseModel):
    # Format RouterOS "<envoi>/<téléchargement>", ex: "2M/2M" ou "512k/1M"
    rate_limit: str = Field(pattern=r"^\d{1,4}[kKmM]/\d{1,4}[kKmM]$")


class HotspotProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60, pattern=r"^[A-Za-z0-9 _-]+$")
    duree_valeur: int = Field(gt=0, le=999)
    duree_unite: Literal["h", "d"]
    partage: int = Field(default=1, ge=1, le=20)
    rate_limit: Optional[str] = Field(default=None, pattern=r"^\d{1,4}[kKmM]/\d{1,4}[kKmM]$")


class HotspotProfileUpdate(BaseModel):
    """Modification d'un forfait existant : seuls les champs envoyés changent.
    Le nom ne se modifie pas (les tickets déjà créés y restent rattachés)."""
    duree_valeur: Optional[int] = Field(default=None, gt=0, le=999)
    duree_unite: Optional[Literal["h", "d"]] = None
    partage: Optional[int] = Field(default=None, ge=1, le=20)
    rate_limit: Optional[str] = Field(default=None, pattern=r"^\d{1,4}[kKmM]/\d{1,4}[kKmM]$")

    @model_validator(mode="after")
    def _duration_needs_unit(self):
        if (self.duree_valeur is None) != (self.duree_unite is None):
            raise ValueError("La durée et son unité (heures ou jours) vont ensemble.")
        return self


class BatchOnlineSaleUpdate(BaseModel):
    online_sale: bool


class HotspotSettingsUpdate(BaseModel):
    """Réglages du HotSpot. Seuls les champs envoyés sont modifiés ;
    une chaîne vide (nom, couleur, préfixe) remet la valeur par défaut."""
    online_sales_enabled: Optional[bool] = None
    brand_name: Optional[str] = None
    brand_color: Optional[str] = None
    brand_slogan: Optional[str] = None
    brand_phone: Optional[str] = None
    code_prefix: Optional[str] = None
    code_length: Optional[int] = None
    code_digits_only: Optional[bool] = None

    @field_validator("brand_slogan")
    @classmethod
    def _check_brand_slogan(cls, v):
        return branding.clean_brand_slogan(v)

    @field_validator("brand_phone")
    @classmethod
    def _check_brand_phone(cls, v):
        return branding.clean_brand_phone(v)

    @field_validator("brand_name")
    @classmethod
    def _check_brand_name(cls, v):
        return branding.clean_brand_name(v)

    @field_validator("brand_color")
    @classmethod
    def _check_brand_color(cls, v):
        return branding.clean_brand_color(v)

    @field_validator("code_prefix")
    @classmethod
    def _check_code_prefix(cls, v):
        return branding.clean_code_prefix(v)


class HotspotSettingsOut(BaseModel):
    online_sales_enabled: bool
    brand_name: Optional[str] = None
    brand_color: Optional[str] = None
    has_logo: bool = False
    logo: Optional[str] = None  # data URI (aperçu)
    brand_slogan: Optional[str] = None
    brand_phone: Optional[str] = None
    has_background: bool = False
    background_url: Optional[str] = None  # adresse de la photo de fond (aperçu)
    code_prefix: Optional[str] = None
    code_length: int = 8
    code_digits_only: bool = False


class HotspotSetupRequest(BaseModel):
    interface: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9 ._-]+$")


# --- Paiement HotSpot en libre-service (page publique, sans authentification) ---

class PublicHotspotPayRequest(BaseModel):
    batch_id: int
    telephone: str = Field(pattern=r"^\+?\d{8,15}$")
    methode: Literal["FLOOZ", "TMONEY"]


# Adresse MAC envoyée par la page HotSpot (variable $(mac) du MikroTik), ex: AA:BB:CC:DD:EE:FF
MAC_PATTERN = r"^[0-9A-Fa-f]{2}([:-][0-9A-Fa-f]{2}){5}$"


class PublicHotspotPayRequest(BaseModel):
    batch_id: int
    telephone: str = Field(pattern=r"^\+?\d{8,15}$")
    methode: Literal["FLOOZ", "TMONEY"]
    mac: Optional[str] = Field(default=None, pattern=MAC_PATTERN)


class PublicHotspotRetrieveRequest(BaseModel):
    telephone: str = Field(pattern=r"^\+?\d{8,15}$")
    mac: Optional[str] = Field(default=None, pattern=MAC_PATTERN)
