from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app import crud, models, schemas, database
import asyncio

app = FastAPI(title="Orders Service")

# DB Dependency
async def get_db_dep():
    async for db in database.get_db():
        yield db

@app.post("/api/v1/orders")
async def create_order(order: schemas.OrderCreate, db: AsyncSession = Depends(get_db_dep)):
    # Dummy user_id
    return await crud.create_order(db, "660e8400-e29b-41d4-a716-446655440000", order)

@app.get("/api/v1/orders")
async def list_orders(page: int = 1, limit: int = 20, status: Optional[str] = None, db: AsyncSession = Depends(get_db_dep)):
    return await crud.get_orders(db, "660e8400-e29b-41d4-a716-446655440000", status, page, limit)

@app.get("/api/v1/orders/{order_id}")
async def get_order(order_id: str, db: AsyncSession = Depends(get_db_dep)):
    return await crud.get_order(db, "660e8400-e29b-41d4-a716-446655440000", order_id)

@app.patch("/api/v1/orders/{order_id}/status")
async def update_order_status(order_id: str, status: dict, db: AsyncSession = Depends(get_db_dep)):
    return await crud.update_order_status(db, order_id, status.get("status"))

@app.delete("/api/v1/orders/{order_id}")
async def delete_order(order_id: str, db: AsyncSession = Depends(get_db_dep)):
    return await crud.delete_order(db, order_id)

@app.get("/api/v1/orders/stats")
async def get_stats(db: AsyncSession = Depends(get_db_dep)):
    return await crud.get_order_stats(db, "660e8400-e29b-41d4-a716-446655440000")
