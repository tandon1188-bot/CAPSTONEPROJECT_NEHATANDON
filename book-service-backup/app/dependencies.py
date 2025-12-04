from fastapi import Header, HTTPException
import os

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "myadmintoken")
INTERNAL_SECRET = os.getenv("INTERNAL_SECRET", "myinternalsecret")

def admin_required(authorization: str = Header(...)):
    if authorization != f"Bearer {ADMIN_TOKEN}":
        raise HTTPException(status_code=403, detail="Forbidden")

def internal_required(x_internal_secret: str = Header(...)):
    if x_internal_secret != INTERNAL_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")
