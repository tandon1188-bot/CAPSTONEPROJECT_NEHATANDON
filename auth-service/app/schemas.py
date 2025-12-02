from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: Optional[str]

from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class UserResponse(BaseModel):
    id: UUID
    email: str
    username: str
    full_name: str | None = None
    is_active: bool
    is_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}  # Pydantic v2


    #lass Config:
        #orm_mode = True
        

class Token(BaseModel):
    access_token: str
    refresh_token: str 
    token_type: str
    expires_in : int
    

# ------------------ REFRESH TOKEN REQUEST ------------------

class RefreshTokenRequest(BaseModel):
    refresh_token: str        # JSON input for refresh endpoint


# ------------------ REFRESH ACCESS TOKEN RESPONSE ------------------

class RefreshTokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int