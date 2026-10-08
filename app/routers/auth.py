from fastapi import APIRouter, Depends, Form, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.database import get_db
from app import models, schemas, security
from app.config import FRONTEND_URL
from app.email_utils import send_reset_email
from app.limiter import limiter

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/register", response_model=schemas.UserOut)
@limiter.limit("5/minute;20/hour")

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
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    remember: bool = Form(True),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()

    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect.",
        )

    token = security.create_access_token(user.id, user.token_version, remember=remember)
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
@limiter.limit("3/minute;10/hour")
def forgot_password(request: Request, payload: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()

    if user:
        token = security.create_reset_token(user.id, user.token_version)
        reset_link = f"{FRONTEND_URL}/reset-password?token={token}"
        try:
            send_reset_email(user.email, reset_link)
        except Exception:
            pass  # on ne révèle jamais une erreur d'envoi au client

    # Réponse identique que le compte existe ou non, pour ne pas divulguer les emails inscrits
    return {"message": "Si un compte existe avec cet email, un lien de réinitialisation vient d'être envoyé."}


@router.post("/reset-password")
@limiter.limit("10/minute")
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
    # Lien demandé avant un autre changement de mot de passe : il n'est plus valable.
    if not security.token_is_current(data, user.token_version):
        raise HTTPException(status_code=400, detail="Lien invalide ou expiré.")

    user.hashed_password = security.hash_password(payload.new_password)
    # Toutes les connexions ouvertes (peut-être par quelqu'un qui connaissait l'ancien mot de
    # passe) sont coupées.
    user.token_version = (user.token_version or 0) + 1
    db.add(models.RevokedToken(token_hash=token_hash))
    db.commit()
    return {"message": "Mot de passe réinitialisé avec succès. Reconnectez-vous sur vos appareils."}


@router.post("/change-password", response_model=schemas.Token)
@limiter.limit("5/minute;20/hour")
def change_password(
    request: Request,
    payload: schemas.ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Change le mot de passe depuis l'application. Les AUTRES appareils sont déconnectés ;
    celui-ci reçoit une nouvelle connexion pour rester connecté."""
    if not security.verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Mot de passe actuel incorrect.")
    if security.verify_password(payload.new_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Le nouveau mot de passe doit être différent de l'actuel.")

    current_user.hashed_password = security.hash_password(payload.new_password)
    current_user.token_version = (current_user.token_version or 0) + 1
    db.commit()
    token = security.create_access_token(current_user.id, current_user.token_version, remember=payload.remember)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout-all")
@limiter.limit("5/minute")
def logout_all(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Déconnecte le compte de TOUS les appareils, y compris celui-ci (téléphone perdu,
    ordinateur partagé oublié connecté...)."""
    current_user.token_version = (current_user.token_version or 0) + 1
    db.commit()
    return {"message": "Vous avez été déconnecté de tous les appareils."}