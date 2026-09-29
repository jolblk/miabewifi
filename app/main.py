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
from app.sync import sync_loop

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Synchronise régulièrement les tickets avec les routeurs (connexions, expirations).
    sync_task = asyncio.create_task(sync_loop())
    yield
    sync_task.cancel()


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

app.include_router(auth.router)
app.include_router(routers_management.router)
app.include_router(wallet.router)
app.include_router(admin.router)
app.include_router(support.router)
app.include_router(hotspot.router)
app.include_router(hotspot_public.router)
@app.get("/health")
def health_check():
    return {"status": "ok"}

app.mount("/assets", StaticFiles(directory="app/static/dist/assets"), name="assets")

@app.get("/{full_path:path}")
def serve_react(full_path: str):
    return FileResponse("app/static/dist/index.html")