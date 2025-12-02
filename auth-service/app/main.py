from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
import json
from datetime import datetime

from app import models, schemas, crud, utils
from app.database import SessionLocal, engine
from app.redis_client import redis_client
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

#from app.utils import verify_password, create_access_token
from fastapi.middleware.cors import CORSMiddleware
import logging
import redis
logging.basicConfig(level=logging.INFO)  # Set global logging level

logging.info("This is an info message")



models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Auth Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
# Optional Redis setup
try:
    import os
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    REDIS_AVAILABLE = True
except Exception:
    redis_client = None
    REDIS_AVAILABLE = False

def get_user_id_from_cache(token: str):
    if not REDIS_AVAILABLE:
        return None
    try:
        return redis_client.get(f"refresh:{token}")
    except Exception:
        return None

def set_user_id_in_cache(token: str, user_id: str, expires: int):
    if not REDIS_AVAILABLE:
        return
    try:
        redis_client.setex(f"refresh:{token}", expires, user_id)
    except Exception:
        pass

@app.post("/api/v1/auth/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if crud.get_user_by_email(db, user.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    if crud.get_user_by_username(db, user.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    
    db_user = crud.create_user(db, user)
    logging.info(f"Created user object: {db_user.__dict__}")
    
    # Cache safely
    try:
        redis_client.set(
            f"user:{db_user.id}",
            json.dumps({
                "email": db_user.email or "",
                "username": db_user.username or "",
                "full_name": db_user.full_name or "",
                "is_active": db_user.is_active
            }),
            ex=3600
        )
    except Exception as e:
        print("Redis caching failed:", e)

    return db_user

# ---------- LOGIN (FORM DATA) ----------
@app.post("/api/v1/auth/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = crud.get_user_by_username(db, form_data.username)
    if not user or not utils.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account inactive")
    
    access_token = utils.create_access_token({"sub": str(user.id)})
    refresh_token = crud.create_refresh_token(db, str(user.id))
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token.token,
        "token_type": "bearer",
        "expires_in": 3600
    }


# ---------- GET CURRENT USER ----------
@app.get("/api/v1/auth/me", response_model=schemas.UserResponse)
def get_me(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = utils.decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


# # -
# @app.post("/api/v1/auth/logout")
# def logout(payload: schemas.RefreshTokenRequest, db: Session = Depends(get_db)):
#     token = db.query(models.RefreshToken).filter(models.RefreshToken.token == payload.refresh_token).first()
#     if token:
#         db.delete(token)
#         db.commit()
#     return {"message": "Successfully logged out"}


# # ---------- UPDATE PROFILE ----------
# @app.put("/api/v1/auth/profile", response_model=schemas.UserResponse)
# def update_profile(profile: schemas.UserUpdate, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
#     payload = utils.decode_access_token(token)
#     user_id = payload.get("sub")
#     if not user_id:
#         raise HTTPException(status_code=401, detail="Invalid token")
    
#     user = db.query(models.User).filter(models.User.id == user_id).first()
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")
    
#     if profile.full_name:
#         user.full_name = profile.full_name
#     if profile.email:
#         user.email = profile.email
#     user.updated_at = datetime.utcnow()
    
#     db.add(user)
#     db.commit()
#     db.refresh(user)
    
#     return user
# #
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hour
REFRESH_TOKEN_EXPIRE_SECONDS = 7 * 24 * 60 * 60  # 7 days

@app.post("/api/v1/auth/refresh", response_model=schemas.RefreshTokenResponse)
def refresh_access_token(
    payload: schemas.RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    refresh_token = payload.refresh_token

    # Check refresh token
    db_token = crud.get_refresh_token(db, refresh_token)
    if not db_token:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if db_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Refresh token expired")

    user_id = db_token.user.id
    # Create NEW access token
    access_token = utils.create_access_token({"sub": str(user_id)})

    # Return ONLY access token
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }