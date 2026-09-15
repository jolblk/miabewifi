from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.database import engine, Base
from app import models
from app.limiter import limiter
from app.routers import auth, routers_management, wallet, admin, notifications, packs_info, support

from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

Base.metadata.create_all(bind=engine)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="MIABEWIFI")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.include_router(notifications.router)
app.include_router(packs_info.router)

# CORS - à restreindre plus tard une fois le frontend défini
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: remplacer par le vrai domaine du frontend en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(routers_management.router)
app.include_router(wallet.router)
app.include_router(admin.router)
app.include_router(support.router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
def read_root():
    return RedirectResponse(url="/static/login.html")