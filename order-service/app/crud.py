from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from uuid import UUID, uuid4
from datetime import datetime

from app.models import Order, OrderItem
from app.schemas import OrderCreate


# ------------------------------------------------------------
# Helper: Serialize SQLAlchemy Order → clean dictionary
# ------------------------------------------------------------
def serialize_order(order: Order):
    return {
        "id": str(order.id),
        "user_id": str(order.user_id),
        "status": order.status,
        "total_amount": float(order.total_amount),
        "created_at": order.created_at.isoformat(),
        "updated_at": order.updated_at.isoformat(),
        "items": [
            {
                "id": str(item.id),
                "book_id": str(item.book_id),
                "book_title": item.book_title,
                "quantity": item.quantity,
                "price_at_purchase": float(item.price_at_purchase),
                "subtotal": float(item.subtotal),
            }
            for item in order.items
        ],
    }


# ------------------------------------------------------------
# CREATE ORDER
# ------------------------------------------------------------
async def create_order(db: AsyncSession, user_id: str, order_data: OrderCreate):
    try:
        user_uuid = UUID(user_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    items = []
    total_amount = 0

    for item in order_data.items:
        try:
            book_uuid = UUID(str(item.book_id))
        except:
            raise HTTPException(status_code=400, detail=f"Invalid book_id: {item.book_id}")

        # Dummy price (replace with call to books-service if needed)
        price = 42.99
        subtotal = price * item.quantity
        total_amount += subtotal

        items.append(
            OrderItem(
                id=uuid4(),
                book_id=book_uuid,
                book_title="Demo Book",
                quantity=item.quantity,
                price_at_purchase=price,
                subtotal=subtotal,
            )
        )

    order = Order(
        id=uuid4(),
        user_id=user_uuid,
        status="pending",
        total_amount=total_amount,
        items=items,
    )

    db.add(order)
    try:
        await db.commit()
        await db.refresh(order)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    # Ensure items are eager-loaded
    result = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order.id)
    )
    order = result.scalar_one()
    return serialize_order(order)


# ------------------------------------------------------------
# LIST ORDERS (pagination)
# ------------------------------------------------------------
async def get_orders(db: AsyncSession, user_id: str, status: str = None, page: int = 1, limit: int = 20):
    try:
        user_uuid = UUID(user_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid user_id")

    base_query = select(Order).where(Order.user_id == user_uuid)

    if status:
        base_query = base_query.where(Order.status == status)

    # Count total
    total_query = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(total_query)).scalar() or 0

    # Pagination
    offset = (page - 1) * limit

    result = await db.execute(
        base_query.options(selectinload(Order.items)).offset(offset).limit(limit)
    )
    orders = result.scalars().unique().all()

    return {
        "items": [serialize_order(o) for o in orders],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
    }


# ------------------------------------------------------------
# GET ORDER BY ID
# ------------------------------------------------------------
async def get_order(db: AsyncSession, user_id: str, order_id: str):
    try:
        order_uuid = UUID(order_id)
        user_uuid = UUID(user_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid UUID")

    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == order_uuid, Order.user_id == user_uuid)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return serialize_order(order)


# ------------------------------------------------------------
# UPDATE ORDER STATUS
# ------------------------------------------------------------
async def update_order_status(db: AsyncSession, order_id: str, new_status: str):
    try:
        order_uuid = UUID(order_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid order_id")

    result = await db.execute(select(Order).where(Order.id == order_uuid))
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = new_status
    order.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(order)

    # Re-fetch for items
    result = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order.id)
    )
    order = result.scalar_one()
    return serialize_order(order)


# ------------------------------------------------------------
# DELETE ORDER
# ------------------------------------------------------------
async def delete_order(db: AsyncSession, order_id: str):
    try:
        order_uuid = UUID(order_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid order_id")

    result = await db.execute(select(Order).where(Order.id == order_uuid))
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != "pending":
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel order (already processing/completed)",
        )

    await db.delete(order)
    await db.commit()
    return serialize_order(order)


# ------------------------------------------------------------
# GET ORDER STATS
# ------------------------------------------------------------
async def get_order_stats(db: AsyncSession, user_id: str):
    try:
        user_uuid = UUID(user_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid user_id")

    # Total orders & total spent
    result = await db.execute(
        select(func.count(Order.id), func.coalesce(func.sum(Order.total_amount), 0))
        .where(Order.user_id == user_uuid)
    )
    total_orders, total_spent = result.first()

    # Orders grouped by status
    group_res = await db.execute(
        select(Order.status, func.count(Order.id))
        .where(Order.user_id == user_uuid)
        .group_by(Order.status)
    )
    orders_by_status = {row[0]: row[1] for row in group_res.fetchall()}

    # Total books purchased
    books_res = await db.execute(
        select(func.coalesce(func.sum(OrderItem.quantity), 0))
        .join(Order)
        .where(Order.user_id == user_uuid)
    )
    total_books = books_res.scalar() or 0

    return {
        "total_orders": total_orders,
        "total_spent": float(total_spent),
        "orders_by_status": orders_by_status,
        "total_books_purchased": total_books,
    }
