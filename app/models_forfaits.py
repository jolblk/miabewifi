"""Réglages commerciaux d'un forfait HotSpot, par routeur : prix, validité, quota.

Le forfait lui-même (durée de connexion, vitesse, appareils) vit sur le MikroTik, qui ne sait
pas ce qu'est un prix. Ce qui concerne la vente est donc rangé ici, rattaché au nom du forfait.
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint

from app.database import Base


class ForfaitSetting(Base):
    __tablename__ = "forfait_settings"
    __table_args__ = (
        UniqueConstraint("router_id", "profile_name", name="uq_forfait_settings_router_profile"),
    )

    id = Column(Integer, primary_key=True, index=True)
    router_id = Column(Integer, ForeignKey("routers.id", ondelete="CASCADE"), nullable=False, index=True)
    profile_name = Column(String, nullable=False)  # nom du forfait sur le MikroTik (ex : "Ticket-1h")
    prix = Column(Integer, nullable=False)          # FCFA
    validite_jours = Column(Integer, nullable=True)  # jours de validité après la 1re connexion
    quota_mo = Column(Integer, nullable=True)        # quota de données par ticket, en Mo
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
