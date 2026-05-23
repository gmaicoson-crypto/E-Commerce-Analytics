from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import (
    AgeGroupEnum,
    CategoryEnum,
    Customer,
    CustomerTypeEnum,
    FinanceCategoryEnum,
    FinanceRecord,
    FinanceTypeEnum,
    GenderEnum,
    Notification,
    NotificationTypeEnum,
    Order,
    OrderItem,
    OrderStatusEnum,
    Product,
    ProductStatusEnum,
    Refund,
)

LARGE_ORDER_THRESHOLD = Decimal("4000")
LOW_STOCK_DEFAULT_THRESHOLD = 10


class IngestError(ValueError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _parse_dt(value: Optional[str]) -> datetime:
    if not value:
        return datetime.utcnow()
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError as exc:
        raise IngestError(f"Invalid datetime: {value}") from exc


def _enum(enum_cls, value, field: str):
    try:
        return enum_cls(value)
    except ValueError as exc:
        raise IngestError(f"Invalid {field}: {value}") from exc


def _money(value, field: str) -> Decimal:
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except Exception as exc:
        raise IngestError(f"Invalid {field}: {value}") from exc


def _enum_value(value):
    return value.value if hasattr(value, "value") else value


def _paginate(query, page: int, page_size: int):
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "rows": rows,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size if total else 0,
        },
    }


def ser_customer(c: Customer) -> Dict[str, Any]:
    return {
        "id": c.id,
        "username": c.username,
        "gender": _enum_value(c.gender),
        "age_group": _enum_value(c.age_group),
        "province": c.province,
        "customer_type": _enum_value(c.customer_type),
        "registered_at": c.registered_at.isoformat() if c.registered_at else None,
    }


def ser_product(p: Product) -> Dict[str, Any]:
    return {
        "id": p.id,
        "product_name": p.product_name,
        "category": _enum_value(p.category),
        "price": float(p.price),
        "cost": float(p.cost),
        "stock": p.stock,
        "low_stock_threshold": p.low_stock_threshold,
        "status": _enum_value(p.status),
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


def ser_order(o: Order) -> Dict[str, Any]:
    return {
        "id": o.id,
        "order_no": o.order_no,
        "customer_id": o.customer_id,
        "customer": o.customer.username if o.customer else None,
        "total_amount": float(o.total_amount),
        "status": _enum_value(o.status),
        "created_at": o.created_at.isoformat() if o.created_at else None,
    }


def ser_finance(f: FinanceRecord) -> Dict[str, Any]:
    return {
        "id": f.id,
        "type": _enum_value(f.type),
        "category": _enum_value(f.category),
        "amount": float(f.amount),
        "related_order_id": f.related_order_id,
        "recorded_at": f.recorded_at.isoformat() if f.recorded_at else None,
    }


def ser_notification(n: Notification) -> Dict[str, Any]:
    return {
        "id": n.id,
        "type": _enum_value(n.type),
        "title": n.title,
        "content": n.content,
        "is_read": bool(n.is_read),
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


def ser_order_item(item: OrderItem) -> Dict[str, Any]:
    return {
        "id": item.id,
        "order_id": item.order_id,
        "product_id": item.product_id,
        "quantity": item.quantity,
        "unit_price": float(item.unit_price),
        "subtotal": float(item.subtotal),
    }


def counts(db: Session) -> Dict[str, int]:
    return {
        "customers": db.query(Customer).count(),
        "products": db.query(Product).count(),
        "orders": db.query(Order).count(),
        "refunds": db.query(Refund).count(),
        "finance_records": db.query(FinanceRecord).count(),
        "notifications": db.query(Notification).count(),
    }


def list_customers(db: Session, page: int, page_size: int, **filters):
    q = db.query(Customer)
    for key in ("gender", "age_group", "province", "customer_type"):
        if filters.get(key):
            q = q.filter(getattr(Customer, key) == filters[key])
    result = _paginate(q.order_by(Customer.id.desc()), page, page_size)
    return {
        "data": [ser_customer(c) for c in result["rows"]],
        "pagination": result["pagination"],
    }


def list_products(db: Session, page: int, page_size: int, category=None, status=None):
    q = db.query(Product)
    if category:
        q = q.filter(Product.category == category)
    if status:
        q = q.filter(Product.status == status)
    result = _paginate(q.order_by(Product.id.desc()), page, page_size)
    return {
        "data": [ser_product(p) for p in result["rows"]],
        "pagination": result["pagination"],
    }


def list_orders(db: Session, page: int, page_size: int, status=None):
    q = db.query(Order)
    if status:
        q = q.filter(Order.status == status)
    result = _paginate(q.order_by(Order.id.desc()), page, page_size)
    return {
        "data": [ser_order(o) for o in result["rows"]],
        "pagination": result["pagination"],
    }


def list_finance(db: Session, page: int, page_size: int, type_=None, category=None):
    q = db.query(FinanceRecord)
    if type_:
        q = q.filter(FinanceRecord.type == type_)
    if category:
        q = q.filter(FinanceRecord.category == category)
    result = _paginate(q.order_by(FinanceRecord.id.desc()), page, page_size)
    return {
        "data": [ser_finance(f) for f in result["rows"]],
        "pagination": result["pagination"],
    }


def list_notifications(
    db: Session, page: int, page_size: int, ntype=None, is_read=None
):
    q = db.query(Notification)
    if ntype:
        q = q.filter(Notification.type == ntype)
    if is_read is not None:
        q = q.filter(Notification.is_read == is_read)
    result = _paginate(q.order_by(Notification.id.desc()), page, page_size)
    return {
        "data": [ser_notification(n) for n in result["rows"]],
        "pagination": result["pagination"],
    }


def create_customer(db: Session, payload) -> Dict[str, Any]:
    c = Customer(
        username=payload.username,
        gender=_enum(GenderEnum, payload.gender, "gender"),
        age_group=_enum(AgeGroupEnum, payload.age_group, "age_group"),
        province=payload.province,
        customer_type=_enum(CustomerTypeEnum, payload.customer_type, "customer_type"),
        registered_at=_parse_dt(payload.registered_at),
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return ser_customer(c)


def update_customer(db: Session, customer_id: int, payload) -> Dict[str, Any]:
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise IngestError("Customer not found", 404)
    for key in ("username", "province"):
        value = getattr(payload, key, None)
        if value is not None:
            setattr(c, key, value)
    if payload.gender is not None:
        c.gender = _enum(GenderEnum, payload.gender, "gender")
    if payload.age_group is not None:
        c.age_group = _enum(AgeGroupEnum, payload.age_group, "age_group")
    if payload.customer_type is not None:
        c.customer_type = _enum(
            CustomerTypeEnum, payload.customer_type, "customer_type"
        )
    db.commit()
    db.refresh(c)
    return ser_customer(c)


def delete_customer(db: Session, customer_id: int) -> Dict[str, Any]:
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise IngestError("Customer not found", 404)
    if db.query(Order).filter(Order.customer_id == customer_id).count() > 0:
        raise IngestError("Customer has orders")
    info = ser_customer(c)
    db.delete(c)
    db.commit()
    return info


def create_product(db: Session, payload) -> Dict[str, Any]:
    p = Product(
        product_name=payload.product_name,
        category=_enum(CategoryEnum, payload.category, "category"),
        price=_money(payload.price, "price"),
        cost=_money(payload.cost, "cost"),
        stock=int(payload.stock),
        low_stock_threshold=int(
            payload.low_stock_threshold or LOW_STOCK_DEFAULT_THRESHOLD
        ),
        status=_enum(ProductStatusEnum, payload.status, "status"),
        created_at=_parse_dt(payload.created_at),
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return ser_product(p)


def update_product(db: Session, product_id: int, payload) -> Dict[str, Any]:
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise IngestError("Product not found", 404)
    for key in ("product_name", "stock", "low_stock_threshold"):
        value = getattr(payload, key, None)
        if value is not None:
            setattr(p, key, value)
    if payload.category is not None:
        p.category = _enum(CategoryEnum, payload.category, "category")
    if payload.status is not None:
        p.status = _enum(ProductStatusEnum, payload.status, "status")
    if payload.price is not None:
        p.price = _money(payload.price, "price")
    if payload.cost is not None:
        p.cost = _money(payload.cost, "cost")
    db.commit()
    db.refresh(p)
    return ser_product(p)


def delete_product(db: Session, product_id: int) -> Dict[str, Any]:
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise IngestError("Product not found", 404)
    if db.query(OrderItem).filter(OrderItem.product_id == product_id).count() > 0:
        raise IngestError("Product is used by orders")
    info = ser_product(p)
    db.delete(p)
    db.commit()
    return info


def _order_no(db: Session, created_at: datetime) -> str:
    seq = (db.query(func.count(Order.id)).scalar() or 0) + 1
    return f"ORD{created_at.strftime('%Y%m%d')}{seq:06d}"


def _add_finance(
    db: Session, type_, category, amount, order_id: Optional[int], recorded_at: datetime
) -> Dict[str, Any]:
    f = FinanceRecord(
        type=type_,
        category=category,
        amount=amount,
        related_order_id=order_id,
        recorded_at=recorded_at,
    )
    db.add(f)
    db.flush()
    return ser_finance(f)


def _add_notification(
    db: Session, ntype, title: str, content: str, created_at: datetime
) -> Dict[str, Any]:
    n = Notification(
        type=ntype, title=title, content=content, is_read=False, created_at=created_at
    )
    db.add(n)
    db.flush()
    return ser_notification(n)


def _maybe_order_notification(
    db: Session, order: Order, created_at: datetime
) -> Optional[Dict[str, Any]]:
    if (order.total_amount or Decimal("0")) < LARGE_ORDER_THRESHOLD:
        return None
    return _add_notification(
        db,
        NotificationTypeEnum.order_alert,
        "大额订单",
        f"订单 {order.order_no} 金额 ¥{float(order.total_amount):.2f}",
        created_at,
    )


def create_order(db: Session, payload) -> Dict[str, Any]:
    customer = db.query(Customer).filter(Customer.id == payload.customer_id).first()
    if not customer:
        raise IngestError("Customer not found")
    if not payload.items:
        raise IngestError("Order items required")

    created_at = _parse_dt(payload.created_at)
    status = _enum(OrderStatusEnum, payload.status, "status")
    order = Order(
        order_no=payload.order_no or _order_no(db, created_at),
        customer_id=customer.id,
        total_amount=Decimal("0.00"),
        status=status,
        created_at=created_at,
        paid_at=(
            created_at
            if status
            in {
                OrderStatusEnum.paid,
                OrderStatusEnum.shipped,
                OrderStatusEnum.completed,
            }
            else None
        ),
        completed_at=created_at if status == OrderStatusEnum.completed else None,
    )
    db.add(order)
    db.flush()

    total = Decimal("0.00")
    cost_total = Decimal("0.00")
    stock_alerts: List[Dict[str, Any]] = []
    for item in payload.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise IngestError(f"Product not found: {item.product_id}")
        qty = int(item.quantity)
        if qty <= 0:
            raise IngestError("Quantity must be positive")
        if product.stock < qty:
            raise IngestError(f"Insufficient stock for product {product.id}")
        unit_price = _money(
            item.unit_price if item.unit_price is not None else product.price,
            "unit_price",
        )
        subtotal = (unit_price * qty).quantize(Decimal("0.01"))
        product.stock -= qty
        total += subtotal
        cost_total += (Decimal(product.cost) * qty).quantize(Decimal("0.01"))
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=qty,
                unit_price=unit_price,
                subtotal=subtotal,
            )
        )
        if product.stock <= product.low_stock_threshold:
            stock_alerts.append(
                _add_notification(
                    db,
                    NotificationTypeEnum.stock_alert,
                    "库存预警",
                    f"{product.product_name} 当前库存 {product.stock},低于阈值 {product.low_stock_threshold}",
                    created_at,
                )
            )

    order.total_amount = total
    finance: List[Dict[str, Any]] = []
    if status in {
        OrderStatusEnum.paid,
        OrderStatusEnum.shipped,
        OrderStatusEnum.completed,
    }:
        finance.extend(_record_order_finance(db, order, cost_total, created_at))

    order_notif = _maybe_order_notification(db, order, created_at)
    notifications = stock_alerts + ([order_notif] if order_notif else [])
    db.commit()
    db.refresh(order)
    return {
        "row": ser_order(order),
        "items": [ser_order_item(i) for i in order.order_items],
        "finance": finance,
        "notifs": notifications,
    }


def _record_order_finance(
    db: Session,
    order: Order,
    cost_total: Optional[Decimal] = None,
    recorded_at: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    recorded_at = recorded_at or datetime.utcnow()
    existing = (
        db.query(FinanceRecord)
        .filter(FinanceRecord.related_order_id == order.id)
        .count()
    )
    if existing:
        return []
    if cost_total is None:
        cost_total = (
            db.query(func.coalesce(func.sum(OrderItem.quantity * Product.cost), 0))
            .join(Product, Product.id == OrderItem.product_id)
            .filter(OrderItem.order_id == order.id)
            .scalar()
        )
        cost_total = Decimal(str(cost_total or 0)).quantize(Decimal("0.01"))
    logistics = Decimal("15.00")
    return [
        _add_finance(
            db,
            FinanceTypeEnum.income,
            FinanceCategoryEnum.sales_income,
            order.total_amount,
            order.id,
            recorded_at,
        ),
        _add_finance(
            db,
            FinanceTypeEnum.expense,
            FinanceCategoryEnum.product_cost,
            cost_total,
            order.id,
            recorded_at,
        ),
        _add_finance(
            db,
            FinanceTypeEnum.expense,
            FinanceCategoryEnum.logistics_cost,
            logistics,
            order.id,
            recorded_at,
        ),
    ]


def update_order_status(db: Session, order_id: int, status: str) -> Dict[str, Any]:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise IngestError("Order not found", 404)
    new_status = _enum(OrderStatusEnum, status, "status")
    allowed = {
        OrderStatusEnum.pending: {OrderStatusEnum.paid, OrderStatusEnum.cancelled},
        OrderStatusEnum.paid: {OrderStatusEnum.shipped},
        OrderStatusEnum.shipped: {OrderStatusEnum.completed},
        OrderStatusEnum.completed: set(),
        OrderStatusEnum.cancelled: set(),
    }
    if new_status != order.status and new_status not in allowed.get(
        order.status, set()
    ):
        raise IngestError("Invalid order status transition")
    now = datetime.utcnow()
    order.status = new_status
    if (
        new_status
        in {OrderStatusEnum.paid, OrderStatusEnum.shipped, OrderStatusEnum.completed}
        and not order.paid_at
    ):
        order.paid_at = now
    if new_status == OrderStatusEnum.completed and not order.completed_at:
        order.completed_at = now
    finance_added = (
        _record_order_finance(db, order, recorded_at=now)
        if new_status
        in {OrderStatusEnum.paid, OrderStatusEnum.shipped, OrderStatusEnum.completed}
        else []
    )
    db.commit()
    db.refresh(order)
    return {
        "row": ser_order(order),
        "finance_added": finance_added,
        "finance_removed": [],
        "notif": None,
    }


def delete_order(db: Session, order_id: int) -> Dict[str, Any]:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise IngestError("Order not found", 404)
    info = ser_order(order)
    db.query(FinanceRecord).filter(FinanceRecord.related_order_id == order.id).delete()
    db.query(Refund).filter(Refund.order_id == order.id).delete()
    db.delete(order)
    db.commit()
    return info


def create_finance(db: Session, payload) -> Dict[str, Any]:
    info = _add_finance(
        db,
        _enum(FinanceTypeEnum, payload.type, "type"),
        _enum(FinanceCategoryEnum, payload.category, "category"),
        _money(payload.amount, "amount"),
        payload.related_order_id,
        _parse_dt(payload.recorded_at),
    )
    db.commit()
    return info


def update_finance(db: Session, finance_id: int, payload) -> Dict[str, Any]:
    f = db.query(FinanceRecord).filter(FinanceRecord.id == finance_id).first()
    if not f:
        raise IngestError("Finance record not found", 404)
    if payload.type is not None:
        f.type = _enum(FinanceTypeEnum, payload.type, "type")
    if payload.category is not None:
        f.category = _enum(FinanceCategoryEnum, payload.category, "category")
    if payload.amount is not None:
        f.amount = _money(payload.amount, "amount")
    db.commit()
    db.refresh(f)
    return ser_finance(f)


def delete_finance(db: Session, finance_id: int) -> Dict[str, Any]:
    f = db.query(FinanceRecord).filter(FinanceRecord.id == finance_id).first()
    if not f:
        raise IngestError("Finance record not found", 404)
    info = ser_finance(f)
    db.delete(f)
    db.commit()
    return info


def create_notification(db: Session, payload) -> Dict[str, Any]:
    info = _add_notification(
        db,
        _enum(NotificationTypeEnum, payload.ntype, "ntype"),
        payload.title,
        payload.content,
        _parse_dt(payload.created_at),
    )
    db.commit()
    return info


def update_notification(db: Session, notification_id: int, payload) -> Dict[str, Any]:
    n = db.query(Notification).filter(Notification.id == notification_id).first()
    if not n:
        raise IngestError("Notification not found", 404)
    for key in ("title", "content", "is_read"):
        value = getattr(payload, key, None)
        if value is not None:
            setattr(n, key, value)
    db.commit()
    db.refresh(n)
    return ser_notification(n)


def delete_notification(db: Session, notification_id: int) -> Dict[str, Any]:
    n = db.query(Notification).filter(Notification.id == notification_id).first()
    if not n:
        raise IngestError("Notification not found", 404)
    info = ser_notification(n)
    db.delete(n)
    db.commit()
    return info


def delete_many(fn, db: Session, ids: Iterable[int]) -> Dict[str, Any]:
    deleted = []
    skipped = []
    for item_id in ids:
        try:
            fn(db, item_id)
            deleted.append(item_id)
        except IngestError as exc:
            skipped.append({"id": item_id, "reason": exc.message})
    return {"deleted": deleted, "skipped": skipped}
