from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from uuid import UUID

class BookCreate(BaseModel):
    title: str
    author: str
    isbn: str
    description: Optional[str]
    price: float
    stock_quantity: int = 0
    category: Optional[str]
    publisher: Optional[str]
    published_date: Optional[date]

class BookUpdate(BaseModel):
    title: Optional[str]
    author: Optional[str]
    isbn: Optional[str]
    description: Optional[str]
    price: Optional[float]
    stock_quantity: Optional[int]
    category: Optional[str]
    publisher: Optional[str]
    published_date: Optional[date]

class StockUpdate(BaseModel):
    quantity_change: int

class BookOut(BaseModel):
    id: UUID
    title: str
    author: str
    isbn: str
    description: Optional[str]
    price: float
    stock_quantity: int
    category: Optional[str]
    publisher: Optional[str]
    published_date: Optional[date]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    # ✅ Pydantic v2 fix for from_orm()
    model_config = {
        "from_attributes": True
    }

