import subprocess
import time
from app.config import WG_AGENT_HOST, WG_AGENT_KEY_PATH

WG_AGENT_USER = "wg-agent"
HANDSHAKE_TIMEOUT_SECONDS = 200  # keepalive côté routeur = 25s, donc au-delà de ~3 min : plus connecté


def _run_agent(command: str) -> str:
    """Exécute une commande sur l'agent WireGuard distant (VPS hôte) via SSH restreint."""
    result = subprocess.run(
        [
            "ssh",
            "-o", "StrictHostKeyChecking=accept-new",
            "-o", "ConnectTimeout=5",
            "-i", WG_AGENT_KEY_PATH,
            f"{WG_AGENT_USER}@{WG_AGENT_HOST}",
            command,
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError(f"wg-agent a échoué : {result.stderr.strip() or result.stdout.strip()}")
    return result.stdout


def add_peer(public_key: str, wireguard_ip: str) -> None:
    _run_agent(f"add-peer {public_key} {wireguard_ip}")


def remove_peer(public_key: str) -> None:
    _run_agent(f"remove-peer {public_key}")


def is_peer_connected(public_key: str) -> bool:
    """Vrai si ce peer a fait une poignée de main WireGuard récente (tunnel actif)."""
    output = _run_agent("list-peers")
    now = int(time.time())
    for line in output.strip().splitlines():
        fields = line.split("\t")
        if len(fields) < 5:
            continue
        peer_public_key = fields[0]
        latest_handshake = int(fields[4])
        if peer_public_key == public_key:
            return latest_handshake > 0 and (now - latest_handshake) < HANDSHAKE_TIMEOUT_SECONDS
    return False