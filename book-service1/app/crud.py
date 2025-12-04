from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc, or_
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from app.models import Book, Category
from app.schemas import BookCreate, BookUpdate, BookOut

# ----------------------
# Create Book
# ----------------------
async def create_book(db: AsyncSession, book_data: BookCreate):
    new_book = Book(**book_data.dict())

    db.add(new_book)
    try:
        await db.commit()
        await db.refresh(new_book)
        return BookOut.from_orm(new_book)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="ISBN already exists")

# ----------------------
# Get Book by ID
# ----------------------
async def get_book(db: AsyncSession, book_id: str):
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return BookOut.from_orm(book)

# ----------------------
# Update Book
# ----------------------
async def update_book(db: AsyncSession, book_id: str, update_data: BookUpdate):
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    for key, value in update_data.dict(exclude_unset=True).items():
        setattr(book, key, value)

    await db.commit()
    await db.refresh(book)
    return BookOut.from_orm(book)

# ----------------------
# Delete Book
# ----------------------
async def delete_book(db: AsyncSession, book_id: str):
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    await db.delete(book)
    await db.commit()

# ----------------------
# List Books with Filters & Pagination
# ----------------------
async def list_books_filtered(
    db: AsyncSession, page: int = 1, limit: int = 20,
    category: str = None, author: str = None, search: str = None,
    min_price: float = None, max_price: float = None,
    sort_by: str = "title", sort_order: str = "asc"
):
    query = select(Book)

    if category:
        query = query.where(Book.category.ilike(f"%{category}%"))
    if author:
        query = query.where(Book.author.ilike(f"%{author}%"))
    if search:
        term = f"%{search}%"
        query = query.where(or_(Book.title.ilike(term), Book.description.ilike(term)))
    if min_price is not None:
        query = query.where(Book.price >= min_price)
    if max_price is not None:
        query = query.where(Book.price <= max_price)

    sort_col = getattr(Book, sort_by, Book.title)
    sort_col = desc(sort_col) if sort_order.lower() == "desc" else asc(sort_col)
    query = query.order_by(sort_col)

    # Pagination
    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0

    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    # ✅ Convert to Pydantic
    items_out = [BookOut.from_orm(b) for b in items]

    pages = (total + limit - 1) // limit
    return {"items": items_out, "total": total, "page": page, "limit": limit, "pages": pages}

# ----------------------
# Get Categories with Book Counts
# ----------------------
async def get_categories_with_count(db: AsyncSession):
    query = (
        select(
            Category.id,
            Category.name,
            Category.description,
            func.count(Book.id).label("book_count")
        )
        .join(Book, Book.category == Category.name, isouter=True)
        .group_by(Category.id)
    )
    result = await db.execute(query)
    return result.all()
