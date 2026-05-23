from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db, settings
from event_bus import bus
from services import ingest_service as svc

router = APIRouter()


class CustomerIn(BaseModel):
    username: str
    gender: str
    age_group: str
    province: str
    customer_type: str
    registered_at: Optional[str] = None


class CustomerUpdateIn(BaseModel):
    username: Optional[str] = None
    gender: Optional[str] = None
    age_group: Optional[str] = None
    province: Optional[str] = None
    customer_type: Optional[str] = None


class ProductIn(BaseModel):
    product_name: str
    category: str
    price: float
    cost: float
    stock: int
    low_stock_threshold: int = 10
    status: str = "on_sale"
    created_at: Optional[str] = None


class ProductUpdateIn(BaseModel):
    product_name: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    cost: Optional[float] = None
    stock: Optional[int] = None
    low_stock_threshold: Optional[int] = None
    status: Optional[str] = None


class OrderItemIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    unit_price: Optional[float] = None


class OrderIn(BaseModel):
    customer_id: int
    items: List[OrderItemIn]
    status: str = "pending"
    order_no: Optional[str] = None
    created_at: Optional[str] = None


class OrderStatusIn(BaseModel):
    status: str


class FinanceIn(BaseModel):
    type: str
    category: str
    amount: float
    related_order_id: Optional[int] = None
    recorded_at: Optional[str] = None


class FinanceUpdateIn(BaseModel):
    type: Optional[str] = None
    category: Optional[str] = None
    amount: Optional[float] = None


class NotificationIn(BaseModel):
    ntype: str
    title: str
    content: str
    created_at: Optional[str] = None


class NotificationUpdateIn(BaseModel):
    is_read: Optional[bool] = None
    title: Optional[str] = None
    content: Optional[str] = None


class BulkDeleteIn(BaseModel):
    ids: List[int]


def _ok(data: Any) -> Dict[str, Any]:
    return {"code": 200, "message": "ok", "data": data}


def _auth(authorization: Optional[str] = Header(default=None)) -> None:
    token = settings.simulator_api_token
    if token and authorization != f"Bearer {token}":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid simulator token"
        )


def _handle(fn):
    try:
        return fn()
    except svc.IngestError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.status_code, "message": exc.message},
        )


def _publish(entity: str, action: str, payload: Dict[str, Any]) -> None:
    bus.publish(entity, action, payload)


def _publish_order_side_effects(result: Dict[str, Any]) -> None:
    for finance in result.get("finance") or result.get("finance_added") or []:
        _publish("finance", "create", finance)
    if result.get("finance_removed"):
        _publish("finance", "delete", {"removed": result["finance_removed"]})
    for notification in result.get("notifs") or []:
        _publish("notification", "create", notification)
    if result.get("notif"):
        _publish("notification", "create", result["notif"])


@router.get("/counts", response_model=dict)
def counts(_: None = Depends(_auth), db: Session = Depends(get_db)):
    return _ok(svc.counts(db))


@router.get("/customers/list", response_model=dict)
def customers_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    gender: Optional[str] = None,
    age_group: Optional[str] = None,
    province: Optional[str] = None,
    customer_type: Optional[str] = None,
    _: None = Depends(_auth),
    db: Session = Depends(get_db),
):
    return _ok(
        svc.list_customers(
            db,
            page,
            page_size,
            gender=gender,
            age_group=age_group,
            province=province,
            customer_type=customer_type,
        )
    )


@router.post("/customers", response_model=dict)
def create_customer(
    body: CustomerIn, _: None = Depends(_auth), db: Session = Depends(get_db)
):
    row = _handle(lambda: svc.create_customer(db, body))
    _publish("customer", "create", row)
    return _ok(row)


@router.patch("/customers/{customer_id}", response_model=dict)
def update_customer(
    customer_id: int,
    body: CustomerUpdateIn,
    _: None = Depends(_auth),
    db: Session = Depends(get_db),
):
    row = _handle(lambda: svc.update_customer(db, customer_id, body))
    _publish("customer", "update", row)
    return _ok(row)


@router.delete("/customers/{customer_id}", response_model=dict)
def delete_customer(
    customer_id: int, _: None = Depends(_auth), db: Session = Depends(get_db)
):
    row = _handle(lambda: svc.delete_customer(db, customer_id))
    _publish("customer", "delete", row)
    return _ok(row)


@router.post("/customers/bulk-delete", response_model=dict)
def delete_customers(
    body: BulkDeleteIn, _: None = Depends(_auth), db: Session = Depends(get_db)
):
    result = svc.delete_many(svc.delete_customer, db, body.ids)
    if result["deleted"]:
        _publish(
            "customer",
            "delete",
            {"ids": result["deleted"], "count": len(result["deleted"])},
        )
    return _ok(result)


@router.get("/products/list", response_model=dict)
def products_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    status: Optional[str] = None,
    _: None = Depends(_auth),
    db: Session = Depends(get_db),
):
    return _ok(svc.list_products(db, page, page_size, category=category, status=status))


@router.post("/products", response_model=dict)
def create_product(
    body: ProductIn, _: None = Depends(_auth), db: Session = Depends(get_db)
):
    row = _handle(lambda: svc.create_product(db, body))
    _publish("product", "create", row)
    return _ok(row)


@router.patch("/products/{product_id}", response_model=dict)
def update_product(
    product_id: int,
    body: ProductUpdateIn,
    _: None = Depends(_auth),
    db: Session = Depends(get_db),
):
    row = _handle(lambda: svc.update_product(db, product_id, body))
    _publish("product", "update", row)
    return _ok(row)


@router.delete("/products/{product_id}", response_model=dict)
def delete_product(
    product_id: int, _: None = Depends(_auth), db: Session = Depends(get_db)
):
    row = _handle(lambda: svc.delete_product(db, product_id))
    _publish("product", "delete", row)
    return _ok(row)


@router.post("/products/bulk-delete", response_model=dict)
def delete_products(
    body: BulkDeleteIn, _: None = Depends(_auth), db: Session = Depends(get_db)
):
    result = svc.delete_many(svc.delete_product, db, body.ids)
    if result["deleted"]:
        _publish(
            "product",
            "delete",
            {"ids": result["deleted"], "count": len(result["deleted"])},
        )
    return _ok(result)


@router.get("/orders/list", response_model=dict)
def orders_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    _: None = Depends(_auth),
    db: Session = Depends(get_db),
):
    return _ok(svc.list_orders(db, page, page_size, status=status))


@router.post("/orders", response_model=dict)
def create_order(
    body: OrderIn, _: None = Depends(_auth), db: Session = Depends(get_db)
):
    result = _handle(lambda: svc.create_order(db, body))
    _publish("order", "create", result["row"])
    _publish_order_side_effects(result)
    return _ok(result)


@router.patch("/orders/{order_id}/status", response_model=dict)
def update_order_status(
    order_id: int,
    body: OrderStatusIn,
    _: None = Depends(_auth),
    db: Session = Depends(get_db),
):
    result = _handle(lambda: svc.update_order_status(db, order_id, body.status))
    _publish("order", "update", result["row"])
    _publish_order_side_effects(result)
    return _ok(result)


@router.delete("/orders/{order_id}", response_model=dict)
def delete_order(
    order_id: int, _: None = Depends(_auth), db: Session = Depends(get_db)
):
    row = _handle(lambda: svc.delete_order(db, order_id))
    _publish("order", "delete", row)
    _publish("finance", "delete", {"order_id": order_id})
    return _ok(row)


@router.post("/orders/bulk-delete", response_model=dict)
def delete_orders(
    body: BulkDeleteIn, _: None = Depends(_auth), db: Session = Depends(get_db)
):
    result = svc.delete_many(svc.delete_order, db, body.ids)
    if result["deleted"]:
        _publish(
            "order",
            "delete",
            {"ids": result["deleted"], "count": len(result["deleted"])},
        )
        _publish("finance", "delete", {"order_ids": result["deleted"]})
    return _ok(result)


@router.get("/finance/list", response_model=dict)
def finance_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: Optional[str] = None,
    category: Optional[str] = None,
    _: None = Depends(_auth),
    db: Session = Depends(get_db),
):
    return _ok(svc.list_finance(db, page, page_size, type_=type, category=category))


@router.post("/finance", response_model=dict)
def create_finance(
    body: FinanceIn, _: None = Depends(_auth), db: Session = Depends(get_db)
):
    row = _handle(lambda: svc.create_finance(db, body))
    _publish("finance", "create", row)
    return _ok(row)


@router.patch("/finance/{finance_id}", response_model=dict)
def update_finance(
    finance_id: int,
    body: FinanceUpdateIn,
    _: None = Depends(_auth),
    db: Session = Depends(get_db),
):
    row = _handle(lambda: svc.update_finance(db, finance_id, body))
    _publish("finance", "update", row)
    return _ok(row)


@router.delete("/finance/{finance_id}", response_model=dict)
def delete_finance(
    finance_id: int, _: None = Depends(_auth), db: Session = Depends(get_db)
):
    row = _handle(lambda: svc.delete_finance(db, finance_id))
    _publish("finance", "delete", row)
    return _ok(row)


@router.get("/notifications/list", response_model=dict)
def notifications_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ntype: Optional[str] = None,
    is_read: Optional[bool] = None,
    _: None = Depends(_auth),
    db: Session = Depends(get_db),
):
    return _ok(
        svc.list_notifications(db, page, page_size, ntype=ntype, is_read=is_read)
    )


@router.post("/notifications", response_model=dict)
def create_notification(
    body: NotificationIn, _: None = Depends(_auth), db: Session = Depends(get_db)
):
    row = _handle(lambda: svc.create_notification(db, body))
    _publish("notification", "create", row)
    return _ok(row)


@router.patch("/notifications/{notification_id}", response_model=dict)
def update_notification(
    notification_id: int,
    body: NotificationUpdateIn,
    _: None = Depends(_auth),
    db: Session = Depends(get_db),
):
    row = _handle(lambda: svc.update_notification(db, notification_id, body))
    _publish("notification", "update", row)
    return _ok(row)


@router.delete("/notifications/{notification_id}", response_model=dict)
def delete_notification(
    notification_id: int, _: None = Depends(_auth), db: Session = Depends(get_db)
):
    row = _handle(lambda: svc.delete_notification(db, notification_id))
    _publish("notification", "delete", row)
    return _ok(row)
