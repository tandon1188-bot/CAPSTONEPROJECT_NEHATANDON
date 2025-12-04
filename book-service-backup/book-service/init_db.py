import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models import Base, Book, Category
from app.config import DATABASE_URL
from datetime import date

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():
    async with engine.begin() as conn:
        print("Creating tables...")
        await conn.run_sync(Base.metadata.create_all)
        print("Tables created!")

    async with AsyncSessionLocal() as session:
        # Sample categories
        categories = [
            {"name": "Programming", "description": "Software development and programming books"},
            {"name": "Fiction", "description": "Fiction and literature"},
            {"name": "Science", "description": "Science and research books"},
        ]
        for c in categories:
            existing = await session.execute(
                Category.__table__.select().where(Category.name == c["name"])
            )
            if not existing.scalar_one_or_none():
                session.add(Category(**c))

        # Sample books
        books = [
            {
                "title": "Clean Code",
                "author": "Robert C. Martin",
                "isbn": "978-0132350884",
                "description": "A handbook of agile software craftsmanship",
                "price": 42.99,
                "stock_quantity": 50,
                "category": "Programming",
                "publisher": "Prentice Hall",
                "published_date": date(2008, 8, 1),
            },
            {
                "title": "The Pragmatic Programmer",
                "author": "Andrew Hunt",
                "isbn": "978-0201616224",
                "description": "From journeyman to master",
                "price": 37.50,
                "stock_quantity": 30,
                "category": "Programming",
                "publisher": "Addison-Wesley",
                "published_date": date(1999, 10, 30),
            },
            {
                "title": "1984",
                "author": "George Orwell",
                "isbn": "978-0451524935",
                "description": "Dystopian social science fiction",
                "price": 15.99,
                "stock_quantity": 100,
                "category": "Fiction",
                "publisher": "Signet Classics",
                "published_date": date(1949, 6, 8),
            },
        ]
        for b in books:
            existing = await session.execute(
                Book.__table__.select().where(Book.isbn == b["isbn"])
            )
            if not existing.scalar_one_or_none():
                session.add(Book(**b))

        await session.commit()
        print("Sample data inserted!")

if __name__ == "__main__":
    asyncio.run(init_db())
