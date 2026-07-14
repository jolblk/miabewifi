import base64
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives import serialization


def generate_keypair() -> tuple[str, str]:
    """Génère une paire de clés WireGuard (privée, publique), encodées en base64."""
    private_key = X25519PrivateKey.generate()

    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    private_b64 = base64.b64encode(private_bytes).decode("utf-8")
    public_b64 = base64.b64encode(public_bytes).decode("utf-8")

    return private_b64, public_b64


def get_next_available_ip(db, models) -> str:
    """Attribue la prochaine IP disponible dans le sous-réseau du tunnel (10.10.0.0/24)."""
    existing_ips = db.query(models.Router.wireguard_ip).all()
    used_last_octets = set()

    for (ip,) in existing_ips:
        if ip:
            last_octet = int(ip.split(".")[-1])
            used_last_octets.add(last_octet)

    for i in range(2, 255):  # .1 réservé au serveur VPS lui-même
        if i not in used_last_octets:
            return f"10.10.0.{i}"

    raise ValueError("Plus d'adresses IP disponibles dans le sous-réseau.")

PORT_RANGES = {
    "winbox": (20000, 29999),
    "webfig": (30000, 39999),
    "ssh": (40000, 49999),
}


def get_next_available_port(db, models, service_type: str) -> int:
    """Attribue le prochain port public disponible pour un type de service donné."""
    start, end = PORT_RANGES[service_type]

    used_ports = {
        p for (p,) in db.query(models.PortMapping.public_port)
        .filter(models.PortMapping.service_type == service_type)
        .all()
    }

    for port in range(start, end + 1):
        if port not in used_ports:
            return port

    raise ValueError(f"Plus de ports disponibles pour {service_type}.")

from datetime import datetime


def is_router_active(db_router) -> bool:
    """Vérifie si un routeur a un accès valide (essai en cours OU abonnement actif)."""
    now = datetime.utcnow()

    if db_router.trial_expires_at and db_router.trial_expires_at > now:
        return True

    if db_router.subscription_expires_at and db_router.subscription_expires_at > now:
        return True

    return False