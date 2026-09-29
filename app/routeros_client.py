import httpx


class RouterOSError(Exception):
    """Erreur renvoyée par l'API REST du routeur, avec le détail lisible."""

    def __init__(self, status_code: int, message: str):
        super().__init__(f"{status_code} {message}")
        self.status_code = status_code
        self.message = message


class RouterOSClient:
    """Client HTTP pour interroger l'API REST RouterOS d'un MikroTik,
    via son adresse privée dans le tunnel WireGuard (ex: 10.10.0.5).

    À utiliser de préférence ainsi, pour réutiliser la même connexion sécurisée
    (beaucoup plus rapide quand on enchaîne des dizaines de requêtes) :

        async with RouterOSClient(ip, user, pwd) as client:
            await client.get_hotspot_users()

    Hors `async with`, chaque appel ouvre sa propre connexion (ancien comportement).
    """

    def __init__(self, router_ip: str, username: str, password: str):
        self.base_url = f"https://{router_ip}/rest"
        self.auth = (username, password)
        self._http: httpx.AsyncClient | None = None

    async def __aenter__(self):
        self._http = httpx.AsyncClient(verify=False, timeout=10, auth=self.auth)
        return self

    async def __aexit__(self, *exc):
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    async def _request(self, method: str, path: str, data: dict | None = None):
        url = f"{self.base_url}/{path}"
        if self._http is not None:
            response = await self._http.request(method, url, json=data)
        else:
            async with httpx.AsyncClient(verify=False, timeout=10, auth=self.auth) as client:
                response = await client.request(method, url, json=data)

        if response.status_code >= 400:
            try:
                body = response.json()
                message = body.get("detail") or body.get("message") or response.text
            except Exception:
                message = response.text
            raise RouterOSError(response.status_code, message)

        return response.json() if response.content else None

    async def get(self, path: str):
        return await self._request("GET", path)

    async def put(self, path: str, data: dict):
        """Crée une entrée (méthode PUT de l'API REST RouterOS)."""
        return await self._request("PUT", path, data)

    async def post(self, path: str, data: dict):
        return await self._request("POST", path, data)

    async def patch(self, path: str, data: dict):
        """Modifie une entrée existante (path se termine par son .id)."""
        return await self._request("PATCH", path, data)

    async def delete(self, path: str):
        return await self._request("DELETE", path)

    async def system_resource(self):
        return await self.get("system/resource")

    async def get_hotspot_servers(self):
        return await self.get("ip/hotspot")

    async def get_hotspot_server_profiles(self):
        return await self.get("ip/hotspot/profile")

    async def get_hotspot_users(self):
        return await self.get("ip/hotspot/user")

    async def get_hotspot_profiles(self):
        return await self.get("ip/hotspot/user/profile")

    async def get_active_sessions(self):
        return await self.get("ip/hotspot/active")

    async def create_hotspot_profile(self, data: dict):
        return await self.put("ip/hotspot/user/profile", data)

    async def update_hotspot_profile(self, profile_id: str, data: dict):
        return await self.patch(f"ip/hotspot/user/profile/{profile_id}", data)

    async def delete_hotspot_profile(self, profile_id: str):
        return await self.delete(f"ip/hotspot/user/profile/{profile_id}")

    async def create_hotspot_user(self, name: str, password: str, profile: str, limit_uptime: str | None = None):
        payload = {"name": name, "password": password, "profile": profile}
        if limit_uptime:
            payload["limit-uptime"] = limit_uptime
        return await self.put("ip/hotspot/user", payload)

    async def delete_hotspot_user(self, user_id: str):
        return await self.delete(f"ip/hotspot/user/{user_id}")

    async def remove_active_session(self, session_id: str):
        return await self.delete(f"ip/hotspot/active/{session_id}")

    async def get_interfaces(self):
        return await self.get("interface")

    async def get_ip_addresses(self):
        return await self.get("ip/address")

    async def write_file(self, name: str, contents: str):
        """Crée ou remplace un fichier texte sur le routeur (ex: page de connexion HotSpot)."""
        files = await self.get("file")
        existing = next((f for f in files if f.get("name") == name), None)
        if existing:
            return await self.patch(f"file/{existing['.id']}", {"contents": contents})
        return await self.put("file", {"name": name, "contents": contents})
