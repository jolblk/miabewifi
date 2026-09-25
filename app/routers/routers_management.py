from app.crypto import decrypt, encrypt
from app.packs import PACKS
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas, wireguard, wg_agent
from app.dependencies import get_current_user
from app.routeros_client import RouterOSClient
from app.config import SERVER_PUBLIC_KEY

router = APIRouter(prefix="/routers", tags=["Routeurs"])

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

    # Déclare ce routeur auprès du serveur WireGuard du VPS : sans ça, le
    # tunnel ne pourra jamais s'établir même si le script est correctement
    # collé dans Winbox.
    try:
        wg_agent.add_peer(public_key, wireguard_ip)
    except Exception as e:
        db.query(models.PortMapping).filter(models.PortMapping.router_id == new_router.id).delete()
        db.delete(new_router)
        db.commit()
        raise HTTPException(
            status_code=502,
            detail=f"Impossible de préparer le serveur pour ce routeur : {e}",
        )

    config_script = f"""/interface/wireguard
add name=wg-miabewifi listen-port=51820 private-key="{private_key}"

/interface/wireguard/peers
add interface=wg-miabewifi public-key="{SERVER_PUBLIC_KEY}" endpoint-address={SERVER_ENDPOINT.split(':')[0]} endpoint-port={SERVER_ENDPOINT.split(':')[1]} allowed-address=10.10.0.0/24 persistent-keepalive=25s

/ip/address
add address={wireguard_ip}/24 interface=wg-miabewifi
"""

    return {"router": new_router, "config_script": config_script}

@router.get("/", response_model=list[schemas.RouterOut])
def list_routers(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return db.query(models.Router).filter(models.Router.owner_id == current_user.id).all()

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

    # "actif" = l'abonnement/essai est valide. "connecte" = le tunnel
    # WireGuard est réellement établi avec ce routeur en ce moment.
    active = wireguard.is_router_active(db_router)

    connected = False
    if db_router.public_key:
        try:
            connected = wg_agent.is_peer_connected(db_router.public_key)
        except Exception:
            # Le sondage échoue ponctuellement (VPS injoignable, etc.) : on
            # ne casse pas l'écran, on retente simplement au prochain sondage.
            connected = db_router.is_connected

    if connected != db_router.is_connected:
        db_router.is_connected = connected
        db.commit()

    return {
        "router_id": db_router.id,
        "actif": active,
        "connecte": connected,
        "trial_expires_at": db_router.trial_expires_at,
        "subscription_expires_at": db_router.subscription_expires_at,
    }


@router.patch("/{router_id}/mikrotik-credentials")
def set_mikrotik_credentials(
    router_id: int,
    data: schemas.MikrotikCredentialsUpdate,
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

    db_router.mikrotik_api_username = data.api_username
    db_router.mikrotik_api_password = encrypt(data.api_password)
    db.commit()

    return {"message": "Identifiants API MikroTik enregistrés."}


@router.get("/{router_id}/mikrotik-status")
async def get_mikrotik_status(
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

    if not db_router.mikrotik_api_username or not db_router.mikrotik_api_password:
        raise HTTPException(status_code=400, detail="Identifiants API MikroTik non configurés pour ce routeur.")

    client = RouterOSClient(
        router_ip=db_router.wireguard_ip,
        username=db_router.mikrotik_api_username,
        password=decrypt(db_router.mikrotik_api_password),
    )

    try:
        data = await client.system_resource()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Impossible de joindre le MikroTik : {e}")

    return data


@router.get("/{router_id}/setup-card")
def download_setup_card(
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

    from app.pdf_generator import generate_router_setup_card
    from app.config import TUTORIAL_VIDEO_URL
    import io
    from fastapi.responses import StreamingResponse

    pdf_bytes = generate_router_setup_card(db_router, TUTORIAL_VIDEO_URL)

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=installation-{db_router.nom}.pdf"},
    )


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

    if db_router.public_key:
        try:
            wg_agent.remove_peer(db_router.public_key)
        except Exception:
            # On ne bloque pas la suppression côté utilisateur pour un souci
            # réseau ponctuel avec le VPS ; l'entrée orpheline pourra être
            # nettoyée manuellement côté serveur si besoin.
            pass

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

    old_public_key = db_router.public_key

    # Génère une NOUVELLE paire de clés (l'ancienne devient invalide)
    private_key, public_key = wireguard.generate_keypair()

    try:
        if old_public_key:
            wg_agent.remove_peer(old_public_key)
        wg_agent.add_peer(public_key, db_router.wireguard_ip)
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Impossible de mettre à jour la configuration sur le serveur : {e}",
        )

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

    # Verrouille la ligne utilisateur pour empêcher deux activations simultanées
    # de dépasser le solde réellement disponible.
    current_user = (
        db.query(models.User)
        .filter(models.User.id == current_user.id)
        .with_for_update()
        .first()
    )
    if current_user.solde < pack["montant"]:
        raise HTTPException(status_code=400, detail="Solde insuffisant. Recharge ton portefeuille.")

    current_user.solde -= pack["montant"]

    base_date = (
        db_router.subscription_expires_at
        if db_router.subscription_expires_at and db_router.subscription_expires_at > datetime.utcnow()
        else datetime.utcnow()
    )
    db_router.subscription_expires_at = base_date + timedelta(days=pack["duree_jours"])

    debit_transaction = models.Transaction(
        user_id=current_user.id,
        montant=pack["montant"],
        methode="PACK",
        statut="confirme",
        type="debit",
        identifier=f"pack-{router_id}-{int(datetime.utcnow().timestamp() * 1000)}",
    )
    db.add(debit_transaction)

    db.commit()
    db.refresh(db_router)

    return {
        "message": f"Pack {pack['label']} activé.",
        "nouveau_solde": current_user.solde,
        "subscription_expires_at": db_router.subscription_expires_at,
    }