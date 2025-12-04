from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class OrderItemCreate(BaseModel):
    book_id: str
    quantity: int

class OrderCreate(BaseModel):
    items: List[OrderItemCreate]

class OrderItemOut(BaseModel):
    book_id: str
    book_title: str
    quantity: int
    price_at_purchase: float
    subtotal: float

    class Config:
        orm_mode = True

class OrderOut(BaseModel):
    id: str
    user_id: str
    status: str
    total_amount: float
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemOut]

    class Config:
        orm_mode = True
