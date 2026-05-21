"""Simulator FastAPI 服务(端口 8001)。

挂载 /api/* 写入端点 + / 静态 UI。每次成功写入都 HTTP POST 给
backend(8000) /api/notify,backend 通过 SSE 广播给主前端 refetch。
"""
from pathlib import Path
from typing import Optional, Any, Dict, List

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
import data_factory as df
from notify_client import notify
from automation import engine as auto_engine


app = FastAPI(title="Data Simulator Service", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)


@app.on_event("startup")
def _startup_sweep_stale_alerts() -> None:
    """启动时清理一次:商品库存已恢复但预警通知遗留的历史记录。"""
    from database import SessionLocal
    with SessionLocal() as db:
        ids = df.sweep_stale_stock_alerts(db)
        if ids:
            print(f"[simulator] startup sweep: removed {len(ids)} stale stock_alert notifications")
            for nid in ids:
                notify("notification", "delete", {"id": nid})


@app.post("/api/maintenance/sweep_stock_alerts")
def api_sweep_stock_alerts(db: Session = Depends(get_db)):
    """手动触发清理:扫描所有 stock_alert,凡商品当前 stock >= threshold 即删。"""
    ids = df.sweep_stale_stock_alerts(db)
    for nid in ids:
        notify("notification", "delete", {"id": nid})
    return _ok({"deleted": len(ids), "ids": ids})


# ─── Pydantic 输入 schema ─────────────────────────────────────────────

class CustomerCreate(BaseModel):
    gender: Optional[str] = None
    age_group: Optional[str] = None
    province: Optional[str] = None
    customer_type: Optional[str] = None
    username: Optional[str] = None


class CustomerBulkCreate(CustomerCreate):
    count: int = 1


class CustomerUpdate(BaseModel):
    username: Optional[str] = None
    gender: Optional[str] = None
    age_group: Optional[str] = None
    province: Optional[str] = None
    customer_type: Optional[str] = None


class ProductCreate(BaseModel):
    category: Optional[str] = None
    status: Optional[str] = None
    price: Optional[float] = None
    cost: Optional[float] = None
    stock: Optional[int] = None


class ProductBulkCreate(ProductCreate):
    count: int = 1


class ProductUpdate(BaseModel):
    product_name: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    price: Optional[float] = None
    cost: Optional[float] = None
    stock: Optional[int] = None
    low_stock_threshold: Optional[int] = None


class OrderCreate(BaseModel):
    status: Optional[str] = None
    customer_id: Optional[int] = None


class OrderUpdate(BaseModel):
    status: Optional[str] = None


class RefundCreate(BaseModel):
    order_id: Optional[int] = None
    amount: Optional[float] = None


class RefundUpdate(BaseModel):
    status: Optional[str] = None
    reason: Optional[str] = None
    refund_amount: Optional[float] = None


class FinanceCreate(BaseModel):
    type: Optional[str] = None
    category: Optional[str] = None
    amount: Optional[float] = None


class FinanceUpdate(BaseModel):
    type: Optional[str] = None
    category: Optional[str] = None
    amount: Optional[float] = None


class NotificationCreate(BaseModel):
    ntype: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None


class NotificationUpdate(BaseModel):
    is_read: Optional[bool] = None
    title: Optional[str] = None
    content: Optional[str] = None


class BulkDeleteBody(BaseModel):
    ids: List[int]


def _ok(data: Any) -> Dict[str, Any]:
    return {"code": 200, "message": "ok", "data": data}


def _err(message: str, code: int = 400):
    raise HTTPException(status_code=code, detail={"code": code, "message": message})


# ─── Counts ────────────────────────────────────────────────────────────

@app.get("/api/counts")
def api_counts(db: Session = Depends(get_db)):
    return _ok(df.get_counts(db))


# ─── Automation(后台协程) ────────────────────────────────────────────

class AutoStartBody(BaseModel):
    events_per_min:        Optional[float] = None
    register_weight:       Optional[float] = None
    # 推进循环
    advances_per_min:      Optional[float] = None
    pending_to_paid:       Optional[float] = None
    pending_to_cancel:     Optional[float] = None
    paid_to_shipped:       Optional[float] = None
    paid_to_refunded:      Optional[float] = None
    shipped_to_completed:  Optional[float] = None
    # 回填模式
    backfill_enabled:      Optional[bool] = None
    backfill_start_date:   Optional[str]  = None
    backfill_end_date:     Optional[str]  = None


@app.post("/api/automation/start")
async def api_auto_start(body: AutoStartBody):
    return _ok(auto_engine.start(**body.model_dump(exclude_none=True)))


@app.post("/api/automation/stop")
async def api_auto_stop():
    return _ok(await auto_engine.stop())


@app.get("/api/automation/status")
def api_auto_status():
    return _ok(auto_engine.status())


# ─── Customer ──────────────────────────────────────────────────────────

@app.get("/api/customer/list")
def api_customer_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    gender: Optional[str] = None,
    age_group: Optional[str] = None,
    province: Optional[str] = None,
    customer_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return _ok(df.list_customers(
        db, page, page_size,
        gender=gender, age_group=age_group, province=province, customer_type=customer_type,
    ))


@app.post("/api/customer")
def api_customer_create(body: CustomerCreate, db: Session = Depends(get_db)):
    info = df.create_customer(
        db, gender=body.gender, age_group=body.age_group,
        province=body.province, customer_type=body.customer_type,
    )
    notify("customer", "create", info)
    return _ok(info)


@app.post("/api/customer/bulk")
def api_customer_bulk_create(body: CustomerBulkCreate, db: Session = Depends(get_db)):
    n = max(1, min(int(body.count), 500))
    created = []
    for _ in range(n):
        info = df.create_customer(
            db, gender=body.gender, age_group=body.age_group,
            province=body.province, customer_type=body.customer_type,
        )
        created.append(info)
    notify("customer", "create", {"bulk": True, "count": len(created)})
    return _ok({"count": len(created), "data": created})


@app.patch("/api/customer/{id}")
def api_customer_update(id: int, body: CustomerUpdate, db: Session = Depends(get_db)):
    info = df.update_customer(db, id, **body.model_dump(exclude_none=True))
    if info is None:
        _err("客户不存在", 404)
    notify("customer", "update", info)
    return _ok(info)


@app.delete("/api/customer/{id}")
def api_customer_delete(id: int, db: Session = Depends(get_db)):
    result = df.delete_customer(db, id)
    if result is None:
        _err("客户不存在", 404)
    if result == "has_orders":
        _err("该客户存在订单,请先删除订单")
    notify("customer", "delete", result)
    return _ok(result)


@app.post("/api/customer/bulk-delete")
def api_customer_bulk_delete(body: BulkDeleteBody, db: Session = Depends(get_db)):
    result = df.delete_customers(db, body.ids)
    if result["deleted"]:
        notify("customer", "delete", {"ids": result["deleted"], "count": len(result["deleted"])})
    return _ok(result)


# ─── Product ───────────────────────────────────────────────────────────

@app.get("/api/product/list")
def api_product_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return _ok(df.list_products(db, page, page_size, category=category, status=status))


@app.post("/api/product")
def api_product_create(body: ProductCreate, db: Session = Depends(get_db)):
    info = df.create_product(
        db, category=body.category, status=body.status,
        price=body.price, cost=body.cost, stock=body.stock,
    )
    notify("product", "create", info)
    return _ok(info)


@app.post("/api/product/bulk")
def api_product_bulk_create(body: ProductBulkCreate, db: Session = Depends(get_db)):
    n = max(1, min(int(body.count), 500))
    created = []
    for _ in range(n):
        info = df.create_product(
            db, category=body.category, status=body.status,
            price=body.price, cost=body.cost, stock=body.stock,
        )
        created.append(info)
    notify("product", "create", {"bulk": True, "count": len(created)})
    return _ok({"count": len(created), "data": created})


@app.patch("/api/product/{id}")
def api_product_update(id: int, body: ProductUpdate, db: Session = Depends(get_db)):
    result = df.update_product(db, id, **body.model_dump(exclude_none=True))
    if result is None:
        _err("商品不存在", 404)
    notify("product", "update", result["row"])
    if result.get("notif"):
        notify("notification", "create", result["notif"])
    for cid in result.get("cleared_notif_ids") or []:
        notify("notification", "delete", {"id": cid})
    return _ok(result["row"])


@app.delete("/api/product/{id}")
def api_product_delete(id: int, db: Session = Depends(get_db)):
    result = df.delete_product(db, id)
    if result is None:
        _err("商品不存在", 404)
    if result == "in_use":
        _err("该商品已被订单引用,无法删除")
    notify("product", "delete", result)
    return _ok(result)


@app.post("/api/product/bulk-delete")
def api_product_bulk_delete(body: BulkDeleteBody, db: Session = Depends(get_db)):
    result = df.delete_products(db, body.ids)
    if result["deleted"]:
        notify("product", "delete", {"ids": result["deleted"], "count": len(result["deleted"])})
    return _ok(result)


# ─── Order ─────────────────────────────────────────────────────────────

@app.get("/api/order/list")
def api_order_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return _ok(df.list_orders(db, page, page_size, status=status))


@app.post("/api/order")
def api_order_create(body: OrderCreate, db: Session = Depends(get_db)):
    result = df.create_order(db, status=body.status, customer_id=body.customer_id)
    if result is None:
        _err("无可用客户或上架商品,无法创建订单")
    notify("order", "create", result["row"])
    if result.get("finance"):
        for f in result["finance"]:
            notify("finance", "create", f)
    for n in result.get("notifs") or []:
        notify("notification", "create", n)
    return _ok(result["row"])


@app.patch("/api/order/{id}")
def api_order_update(id: int, body: OrderUpdate, db: Session = Depends(get_db)):
    result = df.update_order(db, id, status=body.status)
    if result is None:
        _err("订单不存在", 404)
    if result == "invalid_transition":
        _err("当前订单状态不允许此变更", 400)
    notify("order", "update", result["row"])
    if result.get("finance_added"):
        for f in result["finance_added"]:
            notify("finance", "create", f)
    if result.get("finance_removed"):
        notify("finance", "delete", {"order_id": id, "removed": result["finance_removed"]})
    if result.get("notif"):
        notify("notification", "create", result["notif"])
    return _ok(result["row"])


@app.delete("/api/order/{id}")
def api_order_delete(id: int, db: Session = Depends(get_db)):
    info = df.delete_order(db, id)
    if info is None:
        _err("订单不存在", 404)
    notify("order", "delete", info)
    notify("finance", "delete", {"order_id": id})
    return _ok(info)


@app.post("/api/order/bulk-delete")
def api_order_bulk_delete(body: BulkDeleteBody, db: Session = Depends(get_db)):
    result = df.delete_orders(db, body.ids)
    if result["deleted"]:
        notify("order", "delete", {"ids": result["deleted"], "count": len(result["deleted"])})
        notify("finance", "delete", {"order_ids": result["deleted"]})
    return _ok(result)


# ─── Refund ────────────────────────────────────────────────────────────

@app.get("/api/refund/list")
def api_refund_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return _ok(df.list_refunds(db, page, page_size, status=status))


@app.post("/api/refund")
def api_refund_create(body: RefundCreate, db: Session = Depends(get_db)):
    result = df.create_refund(db, order_id=body.order_id, amount=body.amount)
    if result is None:
        _err("无可用 completed 订单(或指定订单已退款)")
    notify("refund", "create", result["row"])
    if result["notif"]:
        notify("notification", "create", result["notif"])
    return _ok(result["row"])


@app.patch("/api/refund/{id}")
def api_refund_update(id: int, body: RefundUpdate, db: Session = Depends(get_db)):
    info = df.update_refund(db, id, **body.model_dump(exclude_none=True))
    if info is None:
        _err("退款记录不存在", 404)
    notify("refund", "update", info)
    return _ok(info)


@app.delete("/api/refund/{id}")
def api_refund_delete(id: int, db: Session = Depends(get_db)):
    info = df.delete_refund(db, id)
    if info is None:
        _err("退款记录不存在", 404)
    notify("refund", "delete", info)
    return _ok(info)


# ─── Finance ───────────────────────────────────────────────────────────

@app.get("/api/finance/list")
def api_finance_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return _ok(df.list_finance_records(db, page, page_size, type_=type, category=category))


@app.post("/api/finance")
def api_finance_create(body: FinanceCreate, db: Session = Depends(get_db)):
    info = df.create_finance_record(
        db, type_=body.type, category=body.category, amount=body.amount,
    )
    notify("finance", "create", info)
    return _ok(info)


@app.patch("/api/finance/{id}")
def api_finance_update(id: int, body: FinanceUpdate, db: Session = Depends(get_db)):
    info = df.update_finance_record(db, id, **body.model_dump(exclude_none=True))
    if info is None:
        _err("财务记录不存在", 404)
    notify("finance", "update", info)
    return _ok(info)


@app.delete("/api/finance/{id}")
def api_finance_delete(id: int, db: Session = Depends(get_db)):
    info = df.delete_finance_record(db, id)
    if info is None:
        _err("财务记录不存在", 404)
    notify("finance", "delete", info)
    return _ok(info)


# ─── Notification ──────────────────────────────────────────────────────

@app.get("/api/notification/list")
def api_notification_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ntype: Optional[str] = None,
    is_read: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    return _ok(df.list_notifications(db, page, page_size, ntype=ntype, is_read=is_read))


@app.post("/api/notification")
def api_notification_create(body: NotificationCreate, db: Session = Depends(get_db)):
    info = df.create_notification(
        db, ntype=body.ntype, title=body.title, content=body.content,
    )
    notify("notification", "create", info)
    return _ok(info)


@app.patch("/api/notification/{id}")
def api_notification_update(id: int, body: NotificationUpdate, db: Session = Depends(get_db)):
    info = df.update_notification(db, id, **body.model_dump(exclude_none=True))
    if info is None:
        _err("通知不存在", 404)
    notify("notification", "update", info)
    return _ok(info)


@app.delete("/api/notification/{id}")
def api_notification_delete(id: int, db: Session = Depends(get_db)):
    info = df.delete_notification(db, id)
    if info is None:
        _err("通知不存在", 404)
    notify("notification", "delete", info)
    return _ok(info)


# ─── 静态 UI ───────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
