from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db, engine
from app import models, crud, schemas, dependencies

app = FastAPI(title="Books Service")


# -----------------------------------------------------
# Startup: Create tables
# -----------------------------------------------------
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)


# -----------------------------------------------------
# STATIC ROUTES MUST COME BEFORE {book_id} ROUTES
# -----------------------------------------------------

# Get all categories
@app.get("/api/v1/books/categories")
async def get_categories(db: AsyncSession = Depends(get_db)):
    categories = await crud.get_categories_with_count(db)
    return {
        "categories": [
            {
                "id": str(c.id),
                "name": c.name,
                "description": c.description,
                "book_count": c.book_count
            }
            for c in categories
        ]
    }


# -----------------------------------------------------
# LIST BOOKS (WITH FILTERS)
# -----------------------------------------------------
@app.get("/api/v1/books", response_model=dict)
async def list_books(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category: str = Query(None),
    author: str = Query(None),
    search: str = Query(None),
    min_price: float = Query(None, ge=0),
    max_price: float = Query(None, ge=0),
    sort_by: str = Query("title", regex="^(price|title|published_date)$"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db)
):
    return await crud.list_books_filtered(
        db, page, limit, category, author, search, min_price, max_price, sort_by, sort_order
    )


# -----------------------------------------------------
# ADMIN ROUTES
# -----------------------------------------------------

# Create Book
@app.post("/api/v1/books", response_model=schemas.BookOut, status_code=201)
async def create_book(
    book: schemas.BookCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(dependencies.admin_required)
):
    return await crud.create_book(db, book)


# Update Book
@app.put("/api/v1/books/{book_id}", response_model=schemas.BookOut)
async def update_book(
    book_id: str,
    book: schemas.BookUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(dependencies.admin_required)
):
    return await crud.update_book(db, book_id, book)


# Delete Book
@app.delete("/api/v1/books/{book_id}", status_code=204)
async def delete_book(
    book_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(dependencies.admin_required)
):
    await crud.delete_book(db, book_id)
    return


# -----------------------------------------------------
# INTERNAL STOCK UPDATE ROUTE
# -----------------------------------------------------
@app.patch("/api/v1/books/{book_id}/stock", response_model=schemas.BookOut)
async def update_stock(
    book_id: str,
    stock: schemas.StockUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(dependencies.internal_required)
):
    book = await crud.get_book(db, book_id)
    new_quantity = book.stock_quantity + stock.quantity_change

    if new_quantity < 0:
        raise HTTPException(status_code=400, detail="Insufficient stock")

    book.stock_quantity = new_quantity
    await db.commit()
    await db.refresh(book)
    return book


# -----------------------------------------------------
# DYNAMIC ROUTE: MUST BE LAST
# -----------------------------------------------------
@app.get("/api/v1/books/{book_id}", response_model=schemas.BookOut)
async def get_book(book_id: str, db: AsyncSession = Depends(get_db)):
    return await crud.get_book(db, book_id)
