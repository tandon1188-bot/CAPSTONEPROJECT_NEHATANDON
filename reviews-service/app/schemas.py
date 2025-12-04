from pydantic import BaseModel
from uuid import UUID
from typing import Optional

class ReviewCreate(BaseModel):
    book_id: UUID
    rating: int
    title: Optional[str] = None
    comment: Optional[str] = None

class ReviewUpdate(BaseModel):
    rating: Optional[int] = None
    title: Optional[str] = None
    comment: Optional[str] = None

class ReviewOut(BaseModel):
    id: UUID
    book_id: UUID
    user_id: UUID
    username: str
    rating: int
    title: Optional[str]
    comment: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        orm_mode = True
