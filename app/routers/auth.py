from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.database import get_db
from app import models, schemas, security
from app.config import FRONTEND_URL
from app.email_utils import send_reset_email
from app.limiter import limiter

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/register", response_model=schemas.UserOut)
@limiter.limit("5/minute")

def register(request: Request, user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Cet email est déjà utilisé.")

    new_user = models.User(
        email=user.email,
        hashed_password=security.hash_password(user.password),
        nom=user.nom,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/login", response_model=schemas.Token)
@limiter.limit("10/minute")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()

    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect.",
        )

    token = security.create_access_token(data={"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}

from app.dependencies import get_current_user, oauth2_scheme as oauth2_scheme_for_logout

@router.get("/me", response_model=schemas.UserOut)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.post("/logout")
def logout(
    token: str = Depends(oauth2_scheme_for_logout),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db.add(models.RevokedToken(token_hash=security.hash_token(token)))
    db.commit()
    return {"message": "Déconnecté."}


@router.post("/forgot-password")
def forgot_password(request: Request, payload: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()

    if user:
        token = security.create_reset_token(user.id)
        reset_link = f"{FRONTEND_URL}/reset-password?token={token}"
        try:
            send_reset_email(user.email, reset_link)
        except Exception:
            pass  # on ne révèle jamais une erreur d'envoi au client

    # Réponse identique que le compte existe ou non, pour ne pas divulguer les emails inscrits
    return {"message": "Si un compte existe avec cet email, un lien de réinitialisation vient d'être envoyé."}


@router.post("/reset-password")
def reset_password(request: Request, payload: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    data = security.decode_reset_token(payload.token)
    if not data:
        raise HTTPException(status_code=400, detail="Lien invalide ou expiré.")

    token_hash = security.hash_token(payload.token)
    if db.query(models.RevokedToken).filter(models.RevokedToken.token_hash == token_hash).first():
        raise HTTPException(status_code=400, detail="Ce lien a déjà été utilisé.")

    user = db.query(models.User).filter(models.User.id == int(data["sub"])).first()
    if not user:
        raise HTTPException(status_code=400, detail="Utilisateur introuvable.")

    user.hashed_password = security.hash_password(payload.new_password)
    db.add(models.RevokedToken(token_hash=token_hash))
    db.commit()
    return {"message": "Mot de passe réinitialisé avec succès."}