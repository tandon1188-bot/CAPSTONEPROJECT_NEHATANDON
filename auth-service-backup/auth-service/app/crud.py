from sqlalchemy.orm import Session
from app import models, utils,schemas
from datetime import datetime
import uuid
import bcrypt

# -------------------------
# USER CRUD
# -------------------------

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()




def create_user(db: Session, user_data: schemas.UserCreate) -> models.User:
    """
    Create a new user in the database with hashed password.
    Password is truncated to 72 bytes to satisfy bcrypt.
    """
    password_bytes = user_data.password.encode("utf-8")
    truncated_bytes = password_bytes[:72]  # bcrypt max 72 bytes
    hashed_bytes = bcrypt.hashpw(truncated_bytes, bcrypt.gensalt())
    hashed_password = hashed_bytes.decode("utf-8")  # store as string in DB

    print("truncated_password:", truncated_bytes.decode("utf-8", errors="ignore"))

    # Create user instance
    user = models.User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        is_active=True  # default active user
    )

    # Add and commit to DB
    db.add(user)
    db.commit()
    db.refresh(user)

    return user

# -------------------------
# REFRESH TOKEN CRUD
# -------------------------

def save_refresh_token(db: Session, user_id: uuid.UUID, token: str, expires_at: datetime):
    rt = models.RefreshToken(
        user_id=user_id,
        token=token,
        expires_at=expires_at
    )
    db.add(rt)
    db.commit()
    db.refresh(rt)
    return rt


def get_refresh_token(db: Session, token: str):
    return db.query(models.RefreshToken).filter(models.RefreshToken.token == token).first()


def delete_refresh_token(db: Session, token: str):
    db_token = get_refresh_token(db, token)
    if db_token:
        db.delete(db_token)
        db.commit()
        return True
    return False
