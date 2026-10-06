import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address


from app.database import engine, Base
from app import models
from app.limiter import limiter
from app.config import FRONTEND_ORIGINS
from app.routers import auth, routers_management, wallet, admin, notifications, packs_info, support, hotspot, hotspot_public
from app.routers import hotspot_forfaits
from app.sync import sync_loop
from app.reconcile import reconcile_loop

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Synchronise régulièrement les tickets avec les routeurs (connexions, expirations).
    sync_task = asyncio.create_task(sync_loop())
    # Rattrape les paiements de tickets dont le webhook PayGate n'est jamais arrivé.
    reconcile_task = asyncio.create_task(reconcile_loop())
    yield
    sync_task.cancel()
    reconcile_task.cancel()


app = FastAPI(title="MIABEWIFI", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.include_router(notifications.router)
app.include_router(packs_info.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# La page HotSpot est servie par le routeur du client (origine différente à chaque
# installation) et n'utilise jamais de cookies/session : ouvrir le CORS uniquement
# sur ces routes publiques est sans risque et évite de devoir lister chaque origine.
@app.middleware("http")
async def public_hotspot_cors(request: Request, call_next):
    if request.url.path.startswith("/public/hotspot"):
        if request.method == "OPTIONS":
            from fastapi.responses import Response
            response = Response(status_code=200)
        else:
            response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response
    return await call_next(request)

# Quand on ouvre ou recharge une page dans le navigateur (en-tête « Accept: text/html »),
# on renvoie toujours l'application React, même si l'adresse porte le même nom qu'une route
# de l'API (ex. /routers/nouveau, /admin/users). Les appels de l'application (axios) ne
# demandent pas du HTML : ils continuent de recevoir du JSON.
SPA_EXCLUDED_PREFIXES = ("/public/", "/docs", "/redoc", "/openapi.json", "/health", "/assets/")


@app.middleware("http")
async def serve_react_to_browsers(request: Request, call_next):
    if (
        request.method in ("GET", "HEAD")
        and "text/html" in request.headers.get("accept", "")
        and not request.url.path.startswith(SPA_EXCLUDED_PREFIXES)
    ):
        return FileResponse("app/static/dist/index.html")
    return await call_next(request)


app.include_router(auth.router)
app.include_router(routers_management.router)
app.include_router(wallet.router)
app.include_router(admin.router)
app.include_router(support.router)
app.include_router(hotspot.router)
app.include_router(hotspot_public.router)
app.include_router(hotspot_forfaits.router)
@app.get("/health")
def health_check():
    return {"status": "ok"}

app.mount("/assets", StaticFiles(directory="app/static/dist/assets"), name="assets")

@app.get("/favicon.svg", include_in_schema=False)
def serve_favicon():
    return FileResponse("app/static/dist/favicon.svg", media_type="image/svg+xml")

@app.get("/{full_path:path}")
def serve_react(full_path: str):
    return FileResponse("app/static/dist/index.html")