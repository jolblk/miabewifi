from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.database import engine, Base
from app import models
from app.routers import auth, routers_management, wallet

Base.metadata.create_all(bind=engine)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="MIABEWIFI")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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

@app.get("/")
def read_root():
    return {"message": "MIABEWIFI - Backend fonctionnel !"}