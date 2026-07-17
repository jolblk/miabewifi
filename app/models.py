from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    nom = Column(String, nullable=False)
    solde = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    routers = relationship("Router", back_populates="owner")


class Router(Base):
    __tablename__ = "routers"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    nom = Column(String, nullable=False)
    wireguard_ip = Column(String, unique=True, nullable=True)
    public_key = Column(String, unique=True, nullable=True)
    is_connected = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    trial_expires_at = Column(DateTime, nullable=True)
    subscription_expires_at = Column(DateTime, nullable=True)  # nouveau champ

    owner = relationship("User", back_populates="routers")
    ports = relationship("PortMapping", back_populates="router")


class PortMapping(Base):
    __tablename__ = "port_mappings"

    id = Column(Integer, primary_key=True, index=True)
    router_id = Column(Integer, ForeignKey("routers.id"), nullable=False)
    service_type = Column(String, nullable=False)  # winbox, webfig, ssh
    public_port = Column(Integer, unique=True, nullable=False)

    router = relationship("Router", back_populates="ports")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    montant = Column(Float, nullable=False)
    methode = Column(String, nullable=False)  # FLOOZ, TMONEY
    statut = Column(String, default="en_attente")
    identifier = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    type = Column(String, default="recharge")  # "recharge" ou "debit"