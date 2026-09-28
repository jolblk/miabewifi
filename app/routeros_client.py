import httpx


class RouterOSClient:
    """Client HTTP pour interroger l'API REST RouterOS d'un MikroTik,
    via son adresse privée dans le tunnel WireGuard (ex: 10.10.0.5)."""

    def __init__(self, router_ip: str, username: str, password: str):
        self.base_url = f"https://{router_ip}/rest"
        self.auth = (username, password)

    async def get(self, path: str):
        async with httpx.AsyncClient(verify=False, timeout=10) as client:
            response = await client.get(f"{self.base_url}/{path}", auth=self.auth)
            response.raise_for_status()
            return response.json()

    async def put(self, path: str, data: dict):
        """Crée une entrée (méthode PUT de l'API REST RouterOS)."""
        async with httpx.AsyncClient(verify=False, timeout=10) as client:
            response = await client.put(f"{self.base_url}/{path}", auth=self.auth, json=data)
            response.raise_for_status()
            return response.json()

    async def post(self, path: str, data: dict):
        async with httpx.AsyncClient(verify=False, timeout=10) as client:
            response = await client.post(f"{self.base_url}/{path}", auth=self.auth, json=data)
            response.raise_for_status()
            return response.json()

    async def system_resource(self):
        return await self.get("system/resource")

    async def get_hotspot_servers(self):
        return await self.get("ip/hotspot")

    async def get_hotspot_users(self):
        return await self.get("ip/hotspot/user")

    async def get_hotspot_profiles(self):
        return await self.get("ip/hotspot/user/profile")

    async def get_active_sessions(self):
        return await self.get("ip/hotspot/active")

    async def create_hotspot_profile(self, data: dict):
        return await self.put("ip/hotspot/user/profile", data)

    async def create_hotspot_user(self, name: str, password: str, profile: str, limit_uptime: str | None = None):
        payload = {"name": name, "password": password, "profile": profile}
        if limit_uptime:
            payload["limit-uptime"] = limit_uptime
        return await self.put("ip/hotspot/user", payload)