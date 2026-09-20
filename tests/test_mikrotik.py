import asyncio
from app.routeros_client import RouterOSClient

# --- À adapter avec les infos de TON MikroTik ---
ROUTER_IP = "192.168.1.64"    # l'IP trouvée à l'étape 1
USERNAME = "uesr1"          # l'utilisateur créé à l'étape 3
PASSWORD = "test1" # son mot de passe
# --------------------------------------------------

async def main():
    client = RouterOSClient(ROUTER_IP, USERNAME, PASSWORD)
    print(f"Connexion à {ROUTER_IP}...")

    try:
        infos = await client.system_resource()
        print("✅ Connexion réussie ! Infos du routeur :")
        print(infos)
    except Exception as e:
        print("❌ Échec de la connexion :", e)


if __name__ == "__main__":
    asyncio.run(main())