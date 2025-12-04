# app/crud.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException
from uuid import UUID, uuid4
from datetime import datetime
from app.models import Review
from app.schemas import ReviewCreate, ReviewUpdate, ReviewOut

# ------------------ CREATE REVIEW ------------------
async def create_review(db: AsyncSession, user_id: UUID, username: str, review_data: ReviewCreate):
    # Check if user already reviewed this book
    existing = await db.execute(
        select(Review).where(Review.book_id == review_data.book_id, Review.user_id == user_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User already reviewed this book")

    review = Review(
        id=uuid4(),
        book_id=review_data.book_id,
        user_id=user_id,
        rating=review_data.rating,
        title=review_data.title,
        comment=review_data.comment,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)

    # Return as Pydantic model with username
    return ReviewOut(
        id=review.id,
        book_id=review.book_id,
        user_id=review.user_id,
        username=username,
        rating=review.rating,
        title=review.title,
        comment=review.comment,
        created_at=review.created_at,
        updated_at=review.updated_at
    )

# ------------------ GET REVIEWS BY BOOK ------------------
async def get_reviews_by_book(db: AsyncSession, book_id: UUID, page: int = 1, limit: int = 20,
                              rating: int = None, sort_by: str = "created_at", sort_order: str = "desc"):
    query = select(Review).where(Review.book_id == book_id)
    if rating:
        query = query.where(Review.rating == rating)

    if sort_by not in {"created_at", "rating"}:
        sort_by = "created_at"
    order_column = getattr(Review, sort_by)
    order_column = order_column.desc() if sort_order == "desc" else order_column.asc()
    query = query.order_by(order_column)

    # Pagination
    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    reviews = result.scalars().all()

    # Map to ReviewOut with placeholder username
    items = [
        ReviewOut(
            id=r.id,
            book_id=r.book_id,
            user_id=r.user_id,
            username="johndoe",  # replace with real username if available
            rating=r.rating,
            title=r.title,
            comment=r.comment,
            created_at=r.created_at,
            updated_at=r.updated_at
        )
        for r in reviews
    ]

    # Average rating
    avg_result = await db.execute(
        select(func.coalesce(func.avg(Review.rating), 0)).where(Review.book_id == book_id)
    )
    average_rating = float(avg_result.scalar() or 0)
    pages = (total + limit - 1) // limit

    return {"items": items, "total": total, "page": page, "limit": limit, "pages": pages, "average_rating": average_rating}

# ------------------ GET REVIEW BY ID ------------------
async def get_review_by_id(db: AsyncSession, review_id: UUID):
    result = await db.execute(select(Review).where(Review.id == review_id))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return ReviewOut(
        id=review.id,
        book_id=review.book_id,
        user_id=review.user_id,
        username="johndoe",  # replace with actual
        rating=review.rating,
        title=review.title,
        comment=review.comment,
        created_at=review.created_at,
        updated_at=review.updated_at
    )

# ------------------ UPDATE REVIEW ------------------
async def update_review(db: AsyncSession, review_id: UUID, user_id: UUID, review_data: ReviewUpdate):
    result = await db.execute(select(Review).where(Review.id == review_id))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    if review.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    if review_data.rating is not None:
        review.rating = review_data.rating
    if review_data.title is not None:
        review.title = review_data.title
    if review_data.comment is not None:
        review.comment = review_data.comment
    review.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(review)

    return ReviewOut(
        id=review.id,
        book_id=review.book_id,
        user_id=review.user_id,
        username="johndoe",
        rating=review.rating,
        title=review.title,
        comment=review.comment,
        created_at=review.created_at,
        updated_at=review.updated_at
    )

# ------------------ DELETE REVIEW ------------------
async def delete_review(db: AsyncSession, review_id: UUID, user_id: UUID):
    result = await db.execute(select(Review).where(Review.id == review_id))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    if review.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    await db.delete(review)
    await db.commit()
    return {"detail": "Review deleted successfully"}

# ------------------ GET USER REVIEWS ------------------
async def get_user_reviews(db: AsyncSession, user_id: UUID, page: int = 1, limit: int = 20):
    query = select(Review).where(Review.user_id == user_id).order_by(Review.created_at.desc())
    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    reviews = result.scalars().all()

    items = [
        ReviewOut(
            id=r.id,
            book_id=r.book_id,
            user_id=r.user_id,
            username="johndoe",
            rating=r.rating,
            title=r.title,
            comment=r.comment,
            created_at=r.created_at,
            updated_at=r.updated_at
        )
        for r in reviews
    ]

    pages = (total + limit - 1) // limit
    return {"items": items, "total": total, "page": page, "limit": limit, "pages": pages}

# ------------------ GET REVIEW SUMMARY ------------------
async def get_review_summary(db: AsyncSession, book_id: UUID):
    total_result = await db.execute(select(func.count(Review.id)).where(Review.book_id == book_id))
    total_reviews = total_result.scalar() or 0

    avg_result = await db.execute(select(func.coalesce(func.avg(Review.rating), 0)).where(Review.book_id == book_id))
    average_rating = float(avg_result.scalar() or 0)

    rating_result = await db.execute(
        select(Review.rating, func.count(Review.id)).where(Review.book_id == book_id).group_by(Review.rating)
    )
    rating_distribution = {row[0]: row[1] for row in rating_result.fetchall()}

    return {
        "book_id": book_id,
        "total_reviews": total_reviews,
        "average_rating": average_rating,
        "rating_distribution": rating_distribution
    }
