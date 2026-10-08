from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, LargeBinary, true, false
from sqlalchemy.orm import relationship, deferred
from datetime import datetime
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    nom = Column(String, nullable=False)
    solde = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    role = Column(String, default="client")  # "client" ou "admin"
    trial_used = Column(Boolean, nullable=False, default=False, server_default=false())  # essai gratuit déjà accordé
    # Augmente à chaque changement de mot de passe ou « déconnexion de tous les appareils » :
    # les connexions ouvertes avant (jetons portant l'ancien numéro) ne sont plus acceptées.
    token_version = Column(Integer, nullable=False, default=0, server_default="0")

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
    # Réglages du HotSpot choisis par le client
    online_sales_enabled = Column(Boolean, nullable=False, default=True, server_default=true())  # vente en libre-service active
    brand_name = Column(String, nullable=True)   # nom affiché sur la page de connexion et les tickets PDF
    brand_color = Column(String, nullable=True)  # couleur principale (#RRGGBB)
    brand_logo = Column(Text, nullable=True)     # logo réduit, en data URI PNG
    brand_slogan = Column(String, nullable=True)  # petite phrase sous le nom, sur la page de connexion
    brand_phone = Column(String, nullable=True)   # téléphone d'aide affiché aux clients du Wi-Fi
    # Photo de fond de la page de connexion (JPEG réduit). « deferred » : chargée seulement quand
    # on la demande, pour ne pas alourdir chaque lecture de routeur (synchro, listes...).
    brand_background = deferred(Column(LargeBinary, nullable=True))
    brand_background_version = Column(String, nullable=True)  # change à chaque nouvelle photo
    code_prefix = Column(String, nullable=True)  # préfixe des codes de tickets (ex: "WIFI")
    code_length = Column(Integer, nullable=False, default=8, server_default="8")  # nombre de caractères après le préfixe
    code_digits_only = Column(Boolean, nullable=False, default=False, server_default=false())  # codes 100 % numériques

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
    montant = Column(Integer, nullable=False)
    methode = Column(String, nullable=False)  # FLOOZ, TMONEY
    statut = Column(String, default="en_attente")
    identifier = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    type = Column(String, default="recharge")  # "recharge", "debit" ou "retrait"
    telephone = Column(String, nullable=True)  # numéro mobile money d'une recharge ou d'un retrait
    note = Column(String, nullable=True)  # motif d'un abonnement offert ou d'une correction de solde (admin)

class VoucherBatch(Base):
    __tablename__ = "voucher_batches"

    id = Column(Integer, primary_key=True, index=True)
    router_id = Column(Integer, ForeignKey("routers.id"), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    profile_name = Column(String, nullable=False)  # nom du profil HotSpot sur le MikroTik
    prix_unitaire = Column(Integer, nullable=False)
    quantite = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    validite_jours = Column(Integer, nullable=True)  # validité calendaire, comptée dès la 1re connexion
    limit_uptime = Column(String, nullable=True)     # durée de connexion cumulée (ex: "1d"), copiée du forfait
    quota_mo = Column(Integer, nullable=True)        # quota de données par ticket en Mo ; NULL = illimité
    online_sale = Column(Boolean, nullable=False, default=True, server_default=true())  # proposé sur la page de paiement en ligne

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
    montant = Column(Integer, nullable=False)
    # NULL = vente en libre-service (payée par le client lui-même, pas par toi/ton équipe)
    vendu_par = Column(Integer, ForeignKey("users.id"), nullable=True)
    vendu_le = Column(DateTime, default=datetime.utcnow)
    acheteur_telephone = Column(String, nullable=True)  # rempli uniquement pour une vente en libre-service
    frais = Column(Integer, nullable=True)  # frais prélevés (FCFA) sur une vente en libre-service ; NULL = aucun

    voucher = relationship("Voucher", back_populates="sale")


class HotspotPurchase(Base):
    """Suit une tentative d'achat de ticket en libre-service (paiement Flooz/T-Money)
    depuis la page de connexion du HotSpot, du clic sur "Payer" jusqu'à la confirmation."""
    __tablename__ = "hotspot_purchases"

    id = Column(Integer, primary_key=True, index=True)
    router_id = Column(Integer, ForeignKey("routers.id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("voucher_batches.id"), nullable=False)
    telephone = Column(String, nullable=False, index=True)
    montant = Column(Integer, nullable=False)
    methode = Column(String, nullable=False)  # FLOOZ, TMONEY
    statut = Column(String, default="en_attente")  # en_attente, confirme, en_rupture, echoue
    identifier = Column(String, unique=True, nullable=False)
    voucher_id = Column(Integer, ForeignKey("vouchers.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    client_mac = Column(String, nullable=True)  # adresse MAC de l'appareil qui a payé (pour « J'ai déjà payé »)


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token_hash = Column(String, unique=True, index=True, nullable=False)
    revoked_at = Column(DateTime, default=datetime.utcnow)