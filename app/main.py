from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address


from app.database import engine, Base
from app import models
from app.limiter import limiter
from app.config import FRONTEND_ORIGINS
from app.routers import auth, routers_management, wallet, admin, notifications, packs_info, support, hotspot

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="MIABEWIFI")
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

app.include_router(auth.router)
app.include_router(routers_management.router)
app.include_router(wallet.router)
app.include_router(admin.router)
app.include_router(support.router)
app.include_router(hotspot.router)
@app.get("/health")
def health_check():
    return {"status": "ok"}

app.mount("/assets", StaticFiles(directory="app/static/dist/assets"), name="assets")

@app.get("/{full_path:path}")
def serve_react(full_path: str):
    return FileResponse("app/static/dist/index.html")