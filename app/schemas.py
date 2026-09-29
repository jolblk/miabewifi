from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Literal, Optional
from urllib.parse import quote_plus


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    nom: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    nom: str
    solde: float
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
    new_password: str = Field(min_length=8)


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

class RechargeRequest(BaseModel):
    phone_number: str
    network: str  # FLOOZ ou TMONEY
    montant: float = Field(gt=0)


class WithdrawRequest(BaseModel):
    phone_number: str
    network: str  # FLOOZ ou TMONEY
    montant: float = Field(gt=0)


class SupportMessage(BaseModel):
    telephone: Optional[str] = None
    sujet: Optional[str] = None
    message: str


class ActivatePackRequest(BaseModel):
    pack_id: str  # "7j", "30j", "90j"

class VoucherBatchCreate(BaseModel):
    profile_name: str
    prix_unitaire: float = Field(gt=0)
    quantite: int = Field(gt=0, le=500)
    # Nombre de jours de validité APRÈS la 1re connexion. Vide = pas de limite calendaire.
    validite_jours: Optional[int] = Field(default=None, ge=1, le=365)


class SaleCreate(BaseModel):
    montant: Optional[float] = None


class SaleOut(BaseModel):
    id: int
    montant: float
    vendu_par: int
    vendu_le: datetime

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
    prix_unitaire: float
    quantite: int
    created_at: datetime
    validite_jours: Optional[int] = None
    limit_uptime: Optional[str] = None
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


class HotspotSetupRequest(BaseModel):
    interface: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9 ._-]+$")
