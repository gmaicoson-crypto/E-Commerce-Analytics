from pathlib import Path
from typing import Optional, Any, Dict, List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import data_factory as df
from automation import engine as auto_engine

# 模拟器服务，监听 8001 端口，提供演示数据接口与静态 UI
app = FastAPI(title="Data Simulator Service", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup_sweep_stale_alerts() -> None:
    # 启动时清理已恢复库存对应的遗留预警通知
    ids = df.sweep_stale_stock_alerts()
    if ids:
        print(f"[simulator] startup sweep: removed {len(ids)} stale stock_alert notifications")


@app.post("/api/maintenance/sweep_stock_alerts")
def api_sweep_stock_alerts():
    # 手动触发清理：库存已恢复的 stock_alert 通知
    ids = df.sweep_stale_stock_alerts()
    return _ok({"deleted": len(ids), "ids": ids})


# ── 请求体 Schema ─────────────────────────────────────────────────────────

class CustomerCreate(BaseModel):
    gender: Optional[str] = None
    age_group: Optional[str] = None
    province: Optional[str] = None
    customer_type: Optional[str] = None


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


# ── 统计 ──────────────────────────────────────────────────────────────────

@app.get("/api/counts")
def api_counts():
    return _ok(df.get_counts())


# ── 自动化（后台协程） ────────────────────────────────────────────────────

class AutoStartBody(BaseModel):
    events_per_min: Optional[float] = None
    register_weight: Optional[float] = None
    advances_per_min: Optional[float] = None
    pending_to_paid: Optional[float] = None
    pending_to_cancel: Optional[float] = None
    paid_to_shipped: Optional[float] = None
    shipped_to_completed: Optional[float] = None
    backfill_enabled: Optional[bool] = None
    backfill_start_date: Optional[str] = None
    backfill_end_date: Optional[str] = None


@app.post("/api/automation/start")
async def api_auto_start(body: AutoStartBody):
    return _ok(auto_engine.start(**body.model_dump(exclude_none=True)))


@app.post("/api/automation/stop")
async def api_auto_stop():
    return _ok(await auto_engine.stop())


@app.get("/api/automation/status")
def api_auto_status():
    return _ok(auto_engine.status())


# ── 客户 ──────────────────────────────────────────────────────────────────

@app.get("/api/customer/list")
def api_customer_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    gender: Optional[str] = None,
    age_group: Optional[str] = None,
    province: Optional[str] = None,
    customer_type: Optional[str] = None,
):
    return _ok(
        df.list_customers(
            page, page_size,
            gender=gender, age_group=age_group,
            province=province, customer_type=customer_type,
        )
    )


@app.post("/api/customer")
def api_customer_create(body: CustomerCreate):
    info = df.create_customer(
        gender=body.gender, age_group=body.age_group,
        province=body.province, customer_type=body.customer_type,
    )
    return _ok(info)


@app.post("/api/customer/bulk")
def api_customer_bulk_create(body: CustomerBulkCreate):
    n = max(1, min(int(body.count), 500))
    created = []
    for _ in range(n):
        info = df.create_customer(
            gender=body.gender, age_group=body.age_group,
            province=body.province, customer_type=body.customer_type,
        )
        created.append(info)
    return _ok({"count": len(created), "data": created})


@app.patch("/api/customer/{id}")
def api_customer_update(id: int, body: CustomerUpdate):
    info = df.update_customer(id, **body.model_dump(exclude_none=True))
    if info is None:
        _err("客户不存在", 404)
    return _ok(info)


@app.delete("/api/customer/{id}")
def api_customer_delete(id: int):
    result = df.delete_customer(id)
    if result is None:
        _err("客户不存在", 404)
    if result == "has_orders":
        _err("该客户存在订单,请先删除订单")
    return _ok(result)


@app.post("/api/customer/bulk-delete")
def api_customer_bulk_delete(body: BulkDeleteBody):
    result = df.delete_customers(body.ids)
    return _ok(result)


# ── 商品 ──────────────────────────────────────────────────────────────────

@app.get("/api/product/list")
def api_product_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    status: Optional[str] = None,
):
    return _ok(df.list_products(page, page_size, category=category, status=status))


@app.post("/api/product")
def api_product_create(body: ProductCreate):
    info = df.create_product(
        category=body.category, status=body.status,
        price=body.price, cost=body.cost, stock=body.stock,
    )
    return _ok(info)


@app.post("/api/product/bulk")
def api_product_bulk_create(body: ProductBulkCreate):
    n = max(1, min(int(body.count), 500))
    created = []
    for _ in range(n):
        info = df.create_product(
            category=body.category, status=body.status,
            price=body.price, cost=body.cost, stock=body.stock,
        )
        created.append(info)
    return _ok({"count": len(created), "data": created})


@app.patch("/api/product/{id}")
def api_product_update(id: int, body: ProductUpdate):
    result = df.update_product(id, **body.model_dump(exclude_none=True))
    if result is None:
        _err("商品不存在", 404)
    return _ok(result["row"])


@app.delete("/api/product/{id}")
def api_product_delete(id: int):
    result = df.delete_product(id)
    if result is None:
        _err("商品不存在", 404)
    if result == "in_use":
        _err("该商品已被订单引用,无法删除")
    return _ok(result)


@app.post("/api/product/bulk-delete")
def api_product_bulk_delete(body: BulkDeleteBody):
    result = df.delete_products(body.ids)
    return _ok(result)


# ── 订单 ──────────────────────────────────────────────────────────────────

@app.get("/api/order/list")
def api_order_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
):
    return _ok(df.list_orders(page, page_size, status=status))


@app.post("/api/order")
def api_order_create(body: OrderCreate):
    result = df.create_order(status=body.status, customer_id=body.customer_id)
    if result is None:
        _err("无可用客户或上架商品,无法创建订单")
    return _ok(result["row"])


@app.patch("/api/order/{id}")
def api_order_update(id: int, body: OrderUpdate):
    result = df.update_order(id, status=body.status)
    if result is None:
        _err("订单不存在", 404)
    if result == "invalid_transition":
        _err("当前订单状态不允许此变更", 400)
    return _ok(result["row"])


@app.delete("/api/order/{id}")
def api_order_delete(id: int):
    info = df.delete_order(id)
    if info is None:
        _err("订单不存在", 404)
    return _ok(info)


@app.post("/api/order/bulk-delete")
def api_order_bulk_delete(body: BulkDeleteBody):
    result = df.delete_orders(body.ids)
    return _ok(result)


# ── 财务 ──────────────────────────────────────────────────────────────────

@app.get("/api/finance/list")
def api_finance_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: Optional[str] = None,
    category: Optional[str] = None,
):
    return _ok(df.list_finance_records(page, page_size, type_=type, category=category))


@app.post("/api/finance")
def api_finance_create(body: FinanceCreate):
    info = df.create_finance_record(type_=body.type, category=body.category, amount=body.amount)
    return _ok(info)


@app.patch("/api/finance/{id}")
def api_finance_update(id: int, body: FinanceUpdate):
    info = df.update_finance_record(id, **body.model_dump(exclude_none=True))
    if info is None:
        _err("财务记录不存在", 404)
    return _ok(info)


@app.delete("/api/finance/{id}")
def api_finance_delete(id: int):
    info = df.delete_finance_record(id)
    if info is None:
        _err("财务记录不存在", 404)
    return _ok(info)


# ── 通知 ──────────────────────────────────────────────────────────────────

@app.get("/api/notification/list")
def api_notification_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ntype: Optional[str] = None,
    is_read: Optional[bool] = None,
):
    return _ok(df.list_notifications(page, page_size, ntype=ntype, is_read=is_read))


@app.post("/api/notification")
def api_notification_create(body: NotificationCreate):
    info = df.create_notification(ntype=body.ntype, title=body.title, content=body.content)
    return _ok(info)


@app.patch("/api/notification/{id}")
def api_notification_update(id: int, body: NotificationUpdate):
    info = df.update_notification(id, **body.model_dump(exclude_none=True))
    if info is None:
        _err("通知不存在", 404)
    return _ok(info)


@app.delete("/api/notification/{id}")
def api_notification_delete(id: int):
    info = df.delete_notification(id)
    if info is None:
        _err("通知不存在", 404)
    return _ok(info)


# ── 静态 UI ───────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001)
