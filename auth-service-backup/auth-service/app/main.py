from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json
import hashlib

from app import models, schemas, crud, utils
from app.database import SessionLocal, engine
from app.redis_client import redis_client
from app.config import ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS
from app.pubsub_client import publish_event   # works only on GCP; safe fallback

# -------------------------
# DB Setup
# -------------------------
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Auth Service (8001)")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# -------------------------
# Dependency
# -------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ----------------------------------------
# REGISTER
# ----------------------------------------
@app.post("/api/v1/auth/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Validate existing user
    if crud.get_user_by_email(db, user.email):
        raise HTTPException(400, "Email already registered")
    if crud.get_user_by_username(db, user.username):
        raise HTTPException(400, "Username already exists")

    # Create user
    new_user = crud.create_user(db, user)

    # Cache user in Redis (1 hour TTL)
    redis_client.setex(
        f"user:{new_user.id}",
        3600,
        json.dumps({
            "email": new_user.email,
            "username": new_user.username,
            "full_name": new_user.full_name,
            "is_active": new_user.is_active
        })
    )

    # Publish event (GCP)
    try:
        publish_event("user.registered", {"user_id": str(new_user.id)})
    except:
        pass

    return new_user


# ----------------------------------------
# LOGIN
# ----------------------------------------
@app.post("/api/v1/auth/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = crud.get_user_by_username(db, form_data.username)
    if not user or not utils.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(401, "Invalid credentials")

    if not user.is_active:
        raise HTTPException(403, "Account inactive")

    # Create JWT access token
    access_token = utils.create_access_token({"sub": str(user.id)})

    # Create JWT refresh token (per spec)
    refresh_token = utils.create_refresh_token({"sub": str(user.id)})
    exp = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    crud.save_refresh_token(db, user.id, refresh_token, exp)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


# ----------------------------------------
# ME — get current user
# ----------------------------------------
@app.get("/api/v1/auth/me", response_model=schemas.UserResponse)
def me(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = utils.decode_access_token(token)
    if not payload:
        raise HTTPException(401, "Invalid or expired access token")

    user_id = payload["sub"]
    user = db.query(models.User).filter(models.User.id == user_id).first()

    if not user:
        raise HTTPException(404, "User not found")

    return user


# ----------------------------------------
# REFRESH TOKEN
# ----------------------------------------
@app.post("/api/v1/auth/refresh", response_model=schemas.RefreshTokenResponse)
def refresh_token(req: schemas.RefreshTokenRequest, db: Session = Depends(get_db)):
    rt = crud.get_refresh_token(db, req.refresh_token)
    if not rt:
        raise HTTPException(401, "Invalid refresh token")

    if rt.expires_at < datetime.utcnow():
        raise HTTPException(401, "Expired refresh token")

    user_id = rt.user_id

    # Create new access token
    access_token = utils.create_access_token({"sub": str(user_id)})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


# ----------------------------------------
# LOGOUT
# ----------------------------------------
@app.post("/api/v1/auth/logout")
def logout(req: schemas.RefreshTokenRequest, db: Session = Depends(get_db)):
    token_hash = hashlib.sha256(req.refresh_token.encode()).hexdigest()

    # Add to blacklist (store for token expiry time)
    redis_client.setex(
        f"token:blacklist:{token_hash}",
        REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        "1"
    )

    crud.delete_refresh_token(db, req.refresh_token)

    return {"message": "Successfully logged out"}


# ----------------------------------------
# UPDATE PROFILE
# ----------------------------------------
@app.put("/api/v1/auth/profile", response_model=schemas.UserResponse)
def update_profile(
    req: schemas.UserUpdate,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    payload = utils.decode_access_token(token)

    if not payload:
        raise HTTPException(401, "Invalid or expired access token")

    user_id = payload["sub"]

    user = db.query(models.User).filter(models.User.id == user_id).first()

    if not user:
        raise HTTPException(404, "User not found")

    if req.full_name:
        user.full_name = req.full_name

    if req.email:
        user.email = req.email

    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    # update Redis cache
    redis_client.setex(
        f"user:{user.id}",
        3600,
        json.dumps({
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "is_active": user.is_active
        })
    )

    # publish update event
    try:
        publish_event("user.updated", {"user_id": str(user.id)})
    except:
        pass

    return user
