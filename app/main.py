from fastapi import FastAPI
from app.database import engine, Base
from app import models
from app.routers import auth, routers_management, wallet

Base.metadata.create_all(bind=engine)

app = FastAPI(title="MIABEWIFI")

app.include_router(auth.router)
app.include_router(routers_management.router)
app.include_router(wallet.router)

@app.get("/")
def read_root():
    return {"message": "MIABEWIFI - Backend fonctionnel !"}