from fastapi import FastAPI, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional
from app.database import async_session
from app.crud import (
    create_review, get_reviews_by_book, get_review_by_id,
    update_review, delete_review, get_user_reviews, get_review_summary
)
from app.schemas import ReviewCreate, ReviewUpdate

app = FastAPI(title="Reviews Service", version="1.0")

async def get_db():
    async with async_session() as session:
        yield session

# Mock current user for demo purposes
async def get_current_user(authorization: str = Header(...)):
    # Extract real user from token in production
    return {"user_id": UUID("660e8400-e29b-41d4-a716-446655440000"), "username": "johndoe"}

@app.post("/api/v1/reviews")
async def api_create_review(review: ReviewCreate, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    return await create_review(db, user["user_id"], user["username"], review)

@app.get("/api/v1/reviews/book/{book_id}")
async def api_get_reviews(book_id: UUID, page:int=1, limit:int=20, rating:Optional[int]=None,
                          sort_by:str="created_at", sort_order:str="desc", db: AsyncSession = Depends(get_db)):
    return await get_reviews_by_book(db, book_id, page, limit, rating, sort_by, sort_order)

@app.get("/api/v1/reviews/{review_id}")
async def api_get_review(review_id: UUID, db: AsyncSession = Depends(get_db)):
    return await get_review_by_id(db, review_id)

@app.put("/api/v1/reviews/{review_id}")
async def api_update_review(review_id: UUID, review: ReviewUpdate, db: AsyncSession = Depends(get_db),
                            user: dict = Depends(get_current_user)):
    return await update_review(db, review_id, user["user_id"], review)

@app.delete("/api/v1/reviews/{review_id}")
async def api_delete_review(review_id: UUID, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    return await delete_review(db, review_id, user["user_id"])

@app.get("/api/v1/reviews/user/me")
async def api_get_user_reviews(page:int=1, limit:int=20, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    return await get_user_reviews(db, user["user_id"], page, limit)

@app.get("/api/v1/reviews/book/{book_id}/summary")
async def api_get_review_summary(book_id: UUID, db: AsyncSession = Depends(get_db)):
    return await get_review_summary(db, book_id)
