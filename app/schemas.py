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