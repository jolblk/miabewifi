from app.packs import PACKS
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas, wireguard
from app.dependencies import get_current_user

router = APIRouter(prefix="/routers", tags=["Routeurs"])

# Clé publique du SERVEUR (VPS) — à générer une fois et mettre dans .env plus tard
SERVER_PUBLIC_KEY = "CLE_PUBLIQUE_SERVEUR_A_DEFINIR"
SERVER_ENDPOINT = "195.35.48.80:51820"  # IP du VPS + port WireGuard standard


@router.post("/", response_model=schemas.RouterConfigOut)
def create_router(
    router_data: schemas.RouterCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    private_key, public_key = wireguard.generate_keypair()
    wireguard_ip = wireguard.get_next_available_ip(db, models)

    new_router = models.Router(
        owner_id=current_user.id,
        nom=router_data.nom,
        wireguard_ip=wireguard_ip,
        public_key=public_key,
        is_connected=False,
        trial_expires_at=datetime.utcnow() + timedelta(days=3),
    )

    db.add(new_router)
    db.commit()
    db.refresh(new_router)

    # Attribution automatique des 3 ports (Winbox, WebFig, SSH)
    for service_type in ["winbox", "webfig", "ssh"]:
        port_number = wireguard.get_next_available_port(db, models, service_type)
        port_mapping = models.PortMapping(
            router_id=new_router.id,
            service_type=service_type,
            public_port=port_number,
        )
        db.add(port_mapping)

    db.commit()
    db.refresh(new_router)

    config_script = f"""/interface/wireguard
add name=wg-miabewifi listen-port=51820 private-key="{private_key}"

/interface/wireguard/peers
add interface=wg-miabewifi public-key="{SERVER_PUBLIC_KEY}" endpoint-address={SERVER_ENDPOINT.split(':')[0]} endpoint-port={SERVER_ENDPOINT.split(':')[1]} allowed-address=10.10.0.0/24 persistent-keepalive=25s

/ip/address
add address={wireguard_ip}/24 interface=wg-miabewifi
"""

    return {"router": new_router, "config_script": config_script}

@router.get("/{router_id}", response_model=schemas.RouterOut)
def get_router(
    router_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_router = (
        db.query(models.Router)
        .filter(models.Router.id == router_id, models.Router.owner_id == current_user.id)
        .first()
    )
    if not db_router:
        raise HTTPException(status_code=404, detail="Routeur introuvable.")
    return db_router

@router.get("/{router_id}/status")
def get_router_status(
    router_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_router = (
        db.query(models.Router)
        .filter(models.Router.id == router_id, models.Router.owner_id == current_user.id)
        .first()
    )
    if not db_router:
        raise HTTPException(status_code=404, detail="Routeur introuvable.")

    active = wireguard.is_router_active(db_router)

    return {
        "router_id": db_router.id,
        "actif": active,
        "trial_expires_at": db_router.trial_expires_at,
        "subscription_expires_at": db_router.subscription_expires_at,
    }


@router.delete("/{router_id}")
def delete_router(
    router_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_router = (
        db.query(models.Router)
        .filter(models.Router.id == router_id, models.Router.owner_id == current_user.id)
        .first()
    )
    if not db_router:
        raise HTTPException(status_code=404, detail="Routeur introuvable.")

    # Supprime d'abord les ports associés (contrainte de clé étrangère)
    db.query(models.PortMapping).filter(models.PortMapping.router_id == router_id).delete()
    db.delete(db_router)
    db.commit()

    return {"message": "Routeur supprimé avec succès."}


@router.post("/{router_id}/regenerate", response_model=schemas.RouterConfigOut)
def regenerate_router_config(
    router_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_router = (
        db.query(models.Router)
        .filter(models.Router.id == router_id, models.Router.owner_id == current_user.id)
        .first()
    )
    if not db_router:
        raise HTTPException(status_code=404, detail="Routeur introuvable.")

    # Génère une NOUVELLE paire de clés (l'ancienne devient invalide)
    private_key, public_key = wireguard.generate_keypair()
    db_router.public_key = public_key
    db_router.is_connected = False
    db.commit()
    db.refresh(db_router)

    config_script = f"""/interface/wireguard
add name=wg-miabewifi listen-port=51820 private-key="{private_key}"

/interface/wireguard/peers
add interface=wg-miabewifi public-key="{SERVER_PUBLIC_KEY}" endpoint-address={SERVER_ENDPOINT.split(':')[0]} endpoint-port={SERVER_ENDPOINT.split(':')[1]} allowed-address=10.10.0.0/24 persistent-keepalive=25s

/ip/address
add address={db_router.wireguard_ip}/24 interface=wg-miabewifi
"""

    return {"router": db_router, "config_script": config_script}

@router.post("/{router_id}/activer-pack")
def activer_pack(
    router_id: int,
    data: schemas.ActivatePackRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    pack = PACKS.get(data.pack_id)
    if not pack:
        raise HTTPException(status_code=400, detail="Pack invalide.")

    db_router = (
        db.query(models.Router)
        .filter(models.Router.id == router_id, models.Router.owner_id == current_user.id)
        .first()
    )
    if not db_router:
        raise HTTPException(status_code=404, detail="Routeur introuvable.")

    if current_user.solde < pack["montant"]:
        raise HTTPException(status_code=400, detail="Solde insuffisant. Recharge ton portefeuille.")

    current_user.solde -= pack["montant"]

    base_date = (
        db_router.subscription_expires_at
        if db_router.subscription_expires_at and db_router.subscription_expires_at > datetime.utcnow()
        else datetime.utcnow()
    )
    db_router.subscription_expires_at = base_date + timedelta(days=pack["duree_jours"])

    db.commit()
    db.refresh(db_router)

    return {
        "message": f"Pack {pack['label']} activé.",
        "nouveau_solde": current_user.solde,
        "subscription_expires_at": db_router.subscription_expires_at,
    }