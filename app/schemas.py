from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional
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
    new_password: str


class RouterCreate(BaseModel):
    nom: str

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
    sale: Optional[SaleOut] = None

    class Config:
        from_attributes = True


class VoucherBatchOut(BaseModel):
    id: int
    profile_name: str
    prix_unitaire: float
    quantite: int
    created_at: datetime
    vouchers: list[VoucherOut] = []

    class Config:
        from_attributes = True