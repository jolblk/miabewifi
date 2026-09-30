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
    role = Column(String, default="client")  # "client" ou "admin"

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
    mikrotik_api_username = Column(String, nullable=True)
    mikrotik_api_password = Column(String, nullable=True)
    subscription_expires_at = Column(DateTime, nullable=True)  # nouveau champ
    setup_mode = Column(String, nullable=False, default="existing", server_default="existing")  # "new" ou "existing"
    wifi_ssid = Column(String, nullable=True)  # nom du Wi-Fi configuré (mode "new")
    public_token = Column(String, unique=True, index=True, nullable=True)  # identifiant public, utilisé par la page hotspot (paiement en libre-service)

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
    type = Column(String, default="recharge")  # "recharge", "debit" ou "retrait"

class VoucherBatch(Base):
    __tablename__ = "voucher_batches"

    id = Column(Integer, primary_key=True, index=True)
    router_id = Column(Integer, ForeignKey("routers.id"), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    profile_name = Column(String, nullable=False)  # nom du profil HotSpot sur le MikroTik
    prix_unitaire = Column(Float, nullable=False)
    quantite = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    validite_jours = Column(Integer, nullable=True)  # validité calendaire, comptée dès la 1re connexion
    limit_uptime = Column(String, nullable=True)     # durée de connexion cumulée (ex: "1d"), copiée du forfait

    vouchers = relationship("Voucher", back_populates="batch")


class Voucher(Base):
    __tablename__ = "vouchers"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("voucher_batches.id"), nullable=False)
    code = Column(String, unique=True, index=True, nullable=False)
    statut = Column(String, default="AVAILABLE")  # AVAILABLE, USED, EXPIRED
    created_at = Column(DateTime, default=datetime.utcnow)
    used_at = Column(DateTime, nullable=True)  # date de vente
    first_login_at = Column(DateTime, nullable=True)  # 1re connexion réelle du client (détectée par la synchro)
    expires_at = Column(DateTime, nullable=True)      # fin de validité calendaire

    batch = relationship("VoucherBatch", back_populates="vouchers")
    sale = relationship("Sale", back_populates="voucher", uselist=False)


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    voucher_id = Column(Integer, ForeignKey("vouchers.id"), unique=True, nullable=False)
    montant = Column(Float, nullable=False)
    # NULL = vente en libre-service (payée par le client lui-même, pas par toi/ton équipe)
    vendu_par = Column(Integer, ForeignKey("users.id"), nullable=True)
    vendu_le = Column(DateTime, default=datetime.utcnow)
    acheteur_telephone = Column(String, nullable=True)  # rempli uniquement pour une vente en libre-service
    frais = Column(Float, nullable=True)  # frais prélevés (FCFA) sur une vente en libre-service ; NULL = aucun

    voucher = relationship("Voucher", back_populates="sale")


class HotspotPurchase(Base):
    """Suit une tentative d'achat de ticket en libre-service (paiement Flooz/T-Money)
    depuis la page de connexion du HotSpot, du clic sur "Payer" jusqu'à la confirmation."""
    __tablename__ = "hotspot_purchases"

    id = Column(Integer, primary_key=True, index=True)
    router_id = Column(Integer, ForeignKey("routers.id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("voucher_batches.id"), nullable=False)
    telephone = Column(String, nullable=False)
    montant = Column(Float, nullable=False)
    methode = Column(String, nullable=False)  # FLOOZ, TMONEY
    statut = Column(String, default="en_attente")  # en_attente, confirme, en_rupture, echoue
    identifier = Column(String, unique=True, nullable=False)
    voucher_id = Column(Integer, ForeignKey("vouchers.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token_hash = Column(String, unique=True, index=True, nullable=False)
    revoked_at = Column(DateTime, default=datetime.utcnow)