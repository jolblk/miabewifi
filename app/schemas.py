from pydantic import BaseModel, EmailStr
from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    nom: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    nom: str
    solde: float
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class RouterCreate(BaseModel):
    nom: str


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

class PortMappingOut(BaseModel):
    service_type: str
    public_port: int

    class Config:
        from_attributes = True

class RechargeRequest(BaseModel):
    phone_number: str
    network: str  # FLOOZ ou TMONEY
    montant: float


class ActivatePackRequest(BaseModel):
    pack_id: str  # "7j", "30j", "90j"