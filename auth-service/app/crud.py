from sqlalchemy.orm import Session
from . import models, utils  # ✅ only import utils here
from datetime import datetime, timedelta
from sqlalchemy.orm import joinedload 
import uuid
import secrets

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()
REFRESH_TOKEN_EXPIRE_DAYS = 30
def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def create_user(db: Session, user_data):
    hashed_password = utils.hash_password(user_data.password)
    db_user = models.User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password,
        full_name=user_data.full_name
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_refresh_token(db: Session, token: str):
    return (
        db.query(models.RefreshToken)
        .options(joinedload(models.RefreshToken.user))
        .filter(models.RefreshToken.token == token)
        .first()
    )

def delete_refresh_token(db: Session, token: str):
    """Optional: removes a refresh token (logout, rotation, etc.)."""
    db_token = (
        db.query(models.RefreshToken)
        .filter(models.RefreshToken.token == token)
        .first()
    )

    if db_token:
        db.delete(db_token)
        db.commit()
        return True

    return False

# ------------------ REFRESH TOKEN CRUD ------------------
def create_refresh_token(db: Session, user_id: uuid.UUID):
    # optional: remove old tokens if you want single active token per user
    # db.query(models.RefreshToken).filter(models.RefreshToken.user_id == user_id).delete()

    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    refresh_token = models.RefreshToken(
        user_id=user_id,
        token=token,
        expires_at=expires_at
    )
    db.add(refresh_token)
    db.commit()
    db.refresh(refresh_token)
    return refresh_token
