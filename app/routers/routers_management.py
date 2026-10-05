import secrets

from app.crypto import decrypt, encrypt
from app.packs import PACKS
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas, wireguard, wg_agent
from app.dependencies import get_current_user
from app.routeros_client import RouterOSClient
from app import mikrotik_scripts
from app.alerts import alert_admins_sync
from app.router_policy import (
    LOW_IP_ALERT_THRESHOLD,
    MAX_UNPAID_ROUTERS,
    TRIAL_DAYS,
    RouterLimitReached,
    decide_router_creation,
)

router = APIRouter(prefix="/routers", tags=["Routeurs"])


@router.post("/", response_model=schemas.RouterConfigOut)
def create_router(
    router_data: schemas.RouterCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Verrouille le compte le temps de la création : deux demandes envoyées en même temps ne
    # peuvent pas obtenir deux essais gratuits ni dépasser ensemble la limite de routeurs.
    owner = (
        db.query(models.User)
        .filter(models.User.id == current_user.id)
        .with_for_update()
        .first()
    )
    unpaid_routers = (
        db.query(models.Router)
        .filter(models.Router.owner_id == owner.id, models.Router.subscription_expires_at.is_(None))
        .count()
    )
    try:
        grant_trial = decide_router_creation(owner.role == "admin", owner.trial_used, unpaid_routers)
    except RouterLimitReached:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=(
                f"Vous avez déjà {MAX_UNPAID_ROUTERS} routeurs sans forfait. Activez un forfait sur l'un "
                "d'eux, ou supprimez celui que vous n'utilisez pas, avant d'en ajouter un autre."
            ),
        )

    private_key, public_key = wireguard.generate_keypair()
    try:
        wireguard_ip = wireguard.get_next_available_ip(db, models)
    except ValueError:
        db.rollback()
        alert_admins_sync("🚨 MIABEWIFI : plus aucune adresse WireGuard libre, les ajouts de routeurs sont bloqués.")
        raise HTTPException(
            status_code=503,
            detail="La plateforme est momentanément complète. Contactez le support.",
        )
    api_password = mikrotik_scripts.generate_api_password()
    # Le nom du Wi-Fi n'a de sens que pour un routeur configuré par MIABEWIFI ("new").
    wifi_ssid = (
        mikrotik_scripts.sanitize_ssid(router_data.wifi_ssid or router_data.nom)
        if router_data.mode == "new"
        else None
    )

    new_router = models.Router(
        owner_id=current_user.id,
        nom=router_data.nom,
        wifi_ssid=wifi_ssid,
        wireguard_ip=wireguard_ip,
        public_key=public_key,
        is_connected=False,
        trial_expires_at=datetime.utcnow() + timedelta(days=TRIAL_DAYS) if grant_trial else None,
        setup_mode=router_data.mode,
        mikrotik_api_username=mikrotik_scripts.API_USERNAME,
        mikrotik_api_password=encrypt(api_password),
        public_token=secrets.token_urlsafe(16),
    )

    db.add(new_router)
    if grant_trial:
        owner.trial_used = True
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
        if grant_trial:
            owner.trial_used = False  # le routeur n'a pas pu être créé : l'essai n'est pas consommé
        db.commit()
        raise HTTPException(
            status_code=502,
            detail=f"Impossible de préparer le serveur pour ce routeur : {e}",
        )

    free_ips = wireguard.count_free_ips(db, models)
    if free_ips <= LOW_IP_ALERT_THRESHOLD:
        alert_admins_sync(
            f"⚠️ MIABEWIFI : il ne reste que {free_ips} adresse(s) WireGuard libre(s) pour de nouveaux routeurs."
        )

    config_script = mikrotik_scripts.build_config_script(
        mode=new_router.setup_mode,
        private_key=private_key,
        wireguard_ip=wireguard_ip,
        api_password=api_password,
        wifi_ssid=new_router.wifi_ssid,
    )

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

    # Supprime d'abord tout ce qui dépend de ce routeur (contraintes de clé étrangère) :
    # les ventes, puis les tickets, puis les lots de tickets, puis les ports.
    batch_ids = db.query(models.VoucherBatch.id).filter(models.VoucherBatch.router_id == router_id).subquery()
    voucher_ids = db.query(models.Voucher.id).filter(models.Voucher.batch_id.in_(batch_ids)).subquery()

    db.query(models.Sale).filter(models.Sale.voucher_id.in_(voucher_ids)).delete(synchronize_session=False)
    db.query(models.Voucher).filter(models.Voucher.batch_id.in_(batch_ids)).delete(synchronize_session=False)
    db.query(models.VoucherBatch).filter(models.VoucherBatch.router_id == router_id).delete(synchronize_session=False)
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
    api_password = mikrotik_scripts.generate_api_password()

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
    db_router.mikrotik_api_username = mikrotik_scripts.API_USERNAME
    db_router.mikrotik_api_password = encrypt(api_password)
    db.commit()
    db.refresh(db_router)

    config_script = mikrotik_scripts.build_config_script(
        mode=db_router.setup_mode,
        private_key=private_key,
        wireguard_ip=db_router.wireguard_ip,
        api_password=api_password,
        wifi_ssid=db_router.wifi_ssid,
    )

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



@router.post("/{router_id}/provision")
async def provision_router(
    router_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Appelé automatiquement par l'assistant dès que le tunnel est établi :
    vérifie que l'API répond, que RouterOS est en v7+, qu'un hotspot existe,
    et crée les forfaits par défaut manquants."""
    db_router = (
        db.query(models.Router)
        .filter(models.Router.id == router_id, models.Router.owner_id == current_user.id)
        .first()
    )
    if not db_router:
        raise HTTPException(status_code=404, detail="Routeur introuvable.")

    if not db_router.mikrotik_api_username or not db_router.mikrotik_api_password:
        raise HTTPException(status_code=400, detail="Identifiants API MikroTik non configurés pour ce routeur.")

    client = _client_for(db_router)

    try:
        resource = await client.system_resource()
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Le routeur est connecté mais son accès de gestion ne répond pas (le script a peut-être été collé partiellement). Détail : {e}",
        )

    version = str(resource.get("version", ""))
    major = version.split(".")[0]
    if not major.isdigit() or int(major) < 7:
        raise HTTPException(
            status_code=400,
            detail=f"RouterOS {version or 'inconnu'} détecté : la version 7 ou plus récente est nécessaire. Mets à jour le routeur puis recommence.",
        )

    return await _prepare_hotspot(client, db_router, version)


async def _prepare_hotspot(client: RouterOSClient, db_router: models.Router, version: str) -> dict:
    """Crée les forfaits par défaut manquants, autorise le paiement en libre-service
    (walled garden) et, pour un routeur configuré par MIABEWIFI, installe la page de
    connexion simplifiée (un seul champ)."""
    if not db_router.public_token:
        # Routeur créé avant l'ajout du paiement en libre-service : on complète maintenant.
        db_router.public_token = secrets.token_urlsafe(16)

    try:
        hotspot_servers = await client.get_hotspot_servers()
        if not hotspot_servers:
            return {"version": version, "hotspot_present": False, "profiles_created": [], "login_page_installed": False}

        existing_names = {p.get("name") for p in await client.get_hotspot_profiles()}
        created = []
        for profile in mikrotik_scripts.DEFAULT_TICKET_PROFILES:
            if profile["name"] not in existing_names:
                await client.create_hotspot_profile(profile)
                created.append(profile["name"])

        # Autorise le client (avant qu'il soit connecté) à joindre l'API MIABEWIFI,
        # seul moyen pour la page HotSpot de déclencher un paiement Flooz/T-Money.
        walled_garden = await client.get_walled_garden()
        if not any(w.get("comment") == mikrotik_scripts.WALLED_GARDEN_COMMENT for w in walled_garden):
            await client.create_walled_garden_rule(
                mikrotik_scripts.PUBLIC_API_HOST, mikrotik_scripts.WALLED_GARDEN_COMMENT,
            )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Impossible de préparer le HotSpot du routeur : {e}")

    # Page de connexion simplifiée : seulement sur un routeur que MIABEWIFI a configuré
    # lui-même, pour ne jamais écraser la page personnalisée d'un routeur existant.
    login_page_installed = False
    if db_router.setup_mode == "new":
        try:
            await client.write_file(
                mikrotik_scripts.LOGIN_PAGE_ROUTER_FILE,
                mikrotik_scripts.render_login_page(
                    db_router.public_token,
                    brand_name=db_router.brand_name,
                    brand_color=db_router.brand_color,
                    brand_logo=db_router.brand_logo,
                ),
            )
            login_page_installed = True
        except Exception:
            login_page_installed = False  # non bloquant : la page par défaut du routeur reste utilisable

    return {
        "version": version,
        "hotspot_present": True,
        "profiles_created": created,
        "login_page_installed": login_page_installed,
    }


def _authorized_router_with_creds(router_id: int, db: Session, current_user: models.User) -> models.Router:
    db_router = (
        db.query(models.Router)
        .filter(models.Router.id == router_id, models.Router.owner_id == current_user.id)
        .first()
    )
    if not db_router:
        raise HTTPException(status_code=404, detail="Routeur introuvable.")
    if not db_router.mikrotik_api_username or not db_router.mikrotik_api_password:
        raise HTTPException(status_code=400, detail="Identifiants API MikroTik non configurés pour ce routeur.")
    return db_router


def _client_for(db_router: models.Router) -> RouterOSClient:
    return RouterOSClient(
        router_ip=db_router.wireguard_ip,
        username=db_router.mikrotik_api_username,
        password=decrypt(db_router.mikrotik_api_password),
    )


@router.get("/{router_id}/lan-interfaces")
async def list_lan_interfaces(
    router_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Interfaces sur lesquelles un HotSpot peut être créé (celles qui ont une adresse IP
    locale). Sert à ajouter un HotSpot sur un routeur déjà en service."""
    db_router = _authorized_router_with_creds(router_id, db, current_user)
    try:
        async with _client_for(db_router) as client:
            interfaces = await client.get_interfaces()
            addresses = await client.get_ip_addresses()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Impossible de joindre le MikroTik : {e}")

    with_ip = {a.get("interface") for a in addresses if a.get("disabled") != "true"}
    result = []
    for itf in interfaces:
        name = itf.get("name")
        if not name or name not in with_ip or name == "wg-miabewifi":
            continue
        if itf.get("type") not in ("bridge", "ether", "vlan"):
            continue
        result.append({"name": name, "type": itf.get("type")})
    return result


@router.post("/{router_id}/setup-hotspot")
async def setup_hotspot(
    router_id: int,
    data: schemas.HotspotSetupRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Ajoute un HotSpot sur une interface d'un routeur déjà en service.
    Les appareils connectés à cette interface devront ensuite saisir un ticket pour accéder à Internet."""
    db_router = _authorized_router_with_creds(router_id, db, current_user)
    try:
        async with _client_for(db_router) as client:
            resource = await client.system_resource()
            version = str(resource.get("version", ""))

            if await client.get_hotspot_servers():
                raise HTTPException(status_code=400, detail="Un HotSpot existe déjà sur ce routeur.")

            addresses = await client.get_ip_addresses()
            addr = next(
                (a for a in addresses if a.get("interface") == data.interface and a.get("disabled") != "true"),
                None,
            )
            if not addr:
                raise HTTPException(status_code=400, detail="Cette interface n'a pas d'adresse IP.")
            hotspot_address = addr["address"].split("/")[0]

            await client.put("ip/hotspot/profile", {
                "name": "miabewifi-hsprof",
                "hotspot-address": hotspot_address,
                "login-by": "cookie,http-chap,http-pap",
            })
            await client.put("ip/hotspot", {
                "name": "miabewifi-hotspot",
                "interface": data.interface,
                "address-pool": "none",
                "profile": "miabewifi-hsprof",
                "disabled": "no",
            })
            return await _prepare_hotspot(client, db_router, version)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Impossible de créer le HotSpot : {e}")