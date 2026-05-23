from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from database import get_db
from dependencies import check_module_permission, get_current_user
from event_bus import bus
from models import CategoryEnum, Product, ProductStatusEnum, Order, OrderItem, Order
from utils import success_response, parse_date_range

router = APIRouter()


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# 创建商品请求体
class ProductCreate(BaseModel):
    product_name: str = Field(min_length=1, max_length=100)
    category: str
    price: float = Field(ge=0)
    cost: float = Field(ge=0)
    stock: int = Field(ge=0)
    low_stock_threshold: int = Field(default=10, ge=0)
    status: str = "on_sale"


# 更新商品请求体（所有字段可选）
class ProductUpdate(BaseModel):
    product_name: str | None = Field(default=None, min_length=1, max_length=100)
    category: str | None = None
    price: float | None = Field(default=None, ge=0)
    cost: float | None = Field(default=None, ge=0)
    stock: int | None = Field(default=None, ge=0)
    low_stock_threshold: int | None = Field(default=None, ge=0)
    status: str | None = None


# 取枚举值字符串
def _enum_value(value):
    return value.value if hasattr(value, "value") else value


# 将 Product 对象序列化为字典
def _product_row(p: Product) -> dict:
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


# 校验并转换品类枚举，无效时返回 400
def _category(value: str) -> CategoryEnum:
    try:
        return CategoryEnum(value)
    except ValueError:
        raise HTTPException(
            status_code=400, detail={"message": f"Invalid category: {value}"}
        )


# 校验并转换商品状态枚举，无效时返回 400
def _status(value: str) -> ProductStatusEnum:
    try:
        return ProductStatusEnum(value)
    except ValueError:
        raise HTTPException(
            status_code=400, detail={"message": f"Invalid status: {value}"}
        )


# 发布商品事件到 SSE 总线
def _publish_product(action: str, payload: dict) -> None:
    bus.publish("product", action, payload)


# 商品管理列表（分页 + 筛选）
@router.get("/manage/list", response_model=dict, dependencies=[Depends(check_module_permission("product_analysis"))])
async def product_manage_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: str | None = None,
    status: str | None = None,
    keyword: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(Product)
    if category:
        q = q.filter(Product.category == category)
    if status:
        q = q.filter(Product.status == status)
    if keyword:
        q = q.filter(Product.product_name.like(f"%{keyword.strip()}%"))
    total = q.count()
    rows = (
        q.order_by(Product.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return success_response(
        {
            "data": [_product_row(p) for p in rows],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size if total else 0,
            },
        }
    )


# 新增商品
@router.post("/manage", response_model=dict, dependencies=[Depends(check_module_permission("product_analysis"))])
async def product_manage_create(
    body: ProductCreate,
    db: Session = Depends(get_db),
):
    product = Product(
        product_name=body.product_name.strip(),
        category=_category(body.category),
        price=Decimal(str(body.price)).quantize(Decimal("0.01")),
        cost=Decimal(str(body.cost)).quantize(Decimal("0.01")),
        stock=body.stock,
        low_stock_threshold=body.low_stock_threshold,
        status=_status(body.status),
        created_at=utc_now(),
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    row = _product_row(product)
    _publish_product("create", row)
    return success_response(row)


# 更新商品信息
@router.patch("/manage/{product_id}", response_model=dict, dependencies=[Depends(check_module_permission("product_analysis"))])
async def product_manage_update(
    product_id: int,
    body: ProductUpdate,
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail={"message": "Product not found"})

    data = body.model_dump(exclude_unset=True)
    if "product_name" in data and data["product_name"] is not None:
        product.product_name = data["product_name"].strip()
    if "category" in data and data["category"] is not None:
        product.category = _category(data["category"])
    if "status" in data and data["status"] is not None:
        product.status = _status(data["status"])
    if "price" in data and data["price"] is not None:
        product.price = Decimal(str(data["price"])).quantize(Decimal("0.01"))
    if "cost" in data and data["cost"] is not None:
        product.cost = Decimal(str(data["cost"])).quantize(Decimal("0.01"))
    for key in ("stock", "low_stock_threshold"):
        if key in data and data[key] is not None:
            setattr(product, key, data[key])

    db.commit()
    db.refresh(product)
    row = _product_row(product)
    _publish_product("update", row)
    return success_response(row)


# 删除商品（有关联订单时拒绝）
@router.delete("/manage/{product_id}", response_model=dict, dependencies=[Depends(check_module_permission("product_analysis"))])
async def product_manage_delete(
    product_id: int,
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail={"message": "Product not found"})
    if db.query(OrderItem).filter(OrderItem.product_id == product_id).count() > 0:
        raise HTTPException(
            status_code=400, detail={"message": "Product is used by orders"}
        )
    row = _product_row(product)
    db.delete(product)
    db.commit()
    _publish_product("delete", row)
    return success_response(row)


# 商品总览统计
@router.get("/overview", response_model=dict, dependencies=[Depends(check_module_permission("product_analysis"))])
async def products_overview(db: Session = Depends(get_db)):
    total_products = db.query(Product).count()
    on_sale = db.query(Product).filter(Product.status == "on_sale").count()
    off_sale = db.query(Product).filter(Product.status == "off_sale").count()
    low_stock = (
        db.query(Product).filter(Product.stock < Product.low_stock_threshold).count()
    )

    total_stock = db.query(func.sum(Product.stock)).scalar() or 0
    total_value = db.query(func.sum(Product.stock * Product.price)).scalar() or Decimal(
        0
    )

    return success_response(
        {
            "total_products": total_products,
            "on_sale": on_sale,
            "off_sale": off_sale,
            "low_stock_count": low_stock,
            "total_stock": int(total_stock),
            "total_inventory_value": float(total_value),
        }
    )


# 按品类统计商品数量、均价、库存
@router.get("/by-category", response_model=dict, dependencies=[Depends(check_module_permission("product_analysis"))])
async def products_by_category(db: Session = Depends(get_db)):
    from sqlalchemy import case

    rows = (
        db.query(
            Product.category.label("category"),
            func.count(Product.id).label("count"),
            func.sum(case((Product.status == "on_sale", 1), else_=0)).label("on_sale"),
            func.coalesce(func.avg(Product.price), 0).label("avg_price"),
            func.coalesce(func.avg(Product.cost), 0).label("avg_cost"),
            func.coalesce(func.sum(Product.stock), 0).label("total_stock"),
        )
        .group_by(Product.category)
        .order_by(Product.category)
        .all()
    )

    data = [
        {
            "category": (
                r.category.value if hasattr(r.category, "value") else r.category
            ),
            "count": int(r.count),
            "on_sale": int(r.on_sale or 0),
            "avg_price": float(r.avg_price),
            "avg_cost": float(r.avg_cost),
            "total_stock": int(r.total_stock),
        }
        for r in rows
    ]

    return success_response(data)


# 库存预警商品列表（库存低于阈值）
@router.get("/low-stock", response_model=dict, dependencies=[Depends(check_module_permission("product_analysis"))])
async def low_stock_products(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    products = (
        db.query(Product)
        .filter(Product.stock < Product.low_stock_threshold)
        .order_by(Product.stock.asc())
        .limit(limit)
        .all()
    )

    data = [
        {
            "id": p.id,
            "product_name": p.product_name,
            "category": p.category.value if p.category else "Unknown",
            "stock": p.stock,
            "low_stock_threshold": p.low_stock_threshold,
            "price": float(p.price),
            "status": p.status,
        }
        for p in products
    ]

    return success_response({"count": len(data), "data": data})


# 横幅滚动热卖榜（任意登录用户可见，不校验模块权限）
@router.get("/highlights", response_model=dict, dependencies=[Depends(get_current_user)])
async def product_highlights(
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(8, ge=1, le=20),
    db: Session = Depends(get_db),
):
    start = date.today() - timedelta(days=days - 1)
    end = date.today()
    rows = (
        db.query(
            Product.product_name.label("product_name"),
            Product.category.label("category"),
            func.coalesce(func.sum(OrderItem.quantity), 0).label("quantity_sold"),
            func.coalesce(func.sum(OrderItem.subtotal), 0).label("sales"),
        )
        .join(OrderItem, OrderItem.product_id == Product.id)
        .join(Order, Order.id == OrderItem.order_id)
        .filter(
            Order.created_at >= datetime.combine(start, datetime.min.time()),
            Order.created_at <= datetime.combine(end, datetime.max.time()),
            Order.status.in_(["paid", "shipped", "completed"]),
        )
        .group_by(Product.product_name, Product.category)
        .order_by(func.sum(OrderItem.subtotal).desc())
        .limit(limit)
        .all()
    )
    return success_response(
        {
            "data": [
                {
                    "product_name": r.product_name,
                    "category": (
                        r.category.value if hasattr(r.category, "value") else r.category
                    ),
                    "quantity_sold": int(r.quantity_sold),
                    "sales": float(r.sales),
                }
                for r in rows
            ]
        }
    )


# 商品销售绩效分析（按销售额排序）
@router.get("/performance", response_model=dict, dependencies=[Depends(check_module_permission("product_analysis"))])
async def product_performance(
    date_range: str = Query("last_7_days"),
    start_date: str = Query(None),
    end_date: str = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    start, end = parse_date_range(date_range, start_date, end_date)

    rows = (
        db.query(
            Product.id.label("product_id"),
            Product.product_name.label("product_name"),
            Product.category.label("category"),
            Product.price.label("price"),
            func.coalesce(func.sum(OrderItem.quantity), 0).label("quantity_sold"),
            func.coalesce(func.sum(OrderItem.subtotal), 0).label("sales"),
            func.coalesce(
                func.sum(OrderItem.subtotal - Product.cost * OrderItem.quantity), 0
            ).label("profit"),
        )
        .join(OrderItem, OrderItem.product_id == Product.id)
        .join(Order, Order.id == OrderItem.order_id)
        .filter(
            Order.created_at >= datetime.combine(start, datetime.min.time()),
            Order.created_at <= datetime.combine(end, datetime.max.time()),
            Order.status.in_(["paid", "shipped", "completed"]),
        )
        .group_by(Product.id, Product.product_name, Product.category, Product.price)
        .order_by(func.sum(OrderItem.subtotal).desc())
        .limit(limit)
        .all()
    )

    data = [
        {
            "product_id": int(r.product_id),
            "product_name": r.product_name,
            "category": (
                r.category.value if hasattr(r.category, "value") else r.category
            ),
            "price": float(r.price),
            "quantity_sold": int(r.quantity_sold),
            "sales": float(r.sales),
            "profit": float(r.profit),
            "profit_margin": float((r.profit / r.sales) * 100) if r.sales else 0,
        }
        for r in rows
    ]

    return success_response(
        {
            "period": {"start": start.isoformat(), "end": end.isoformat()},
            "data": data,
        }
    )


# TOP-N 商品近 N 天日销量曲线
@router.get("/top-trend", response_model=dict, dependencies=[Depends(check_module_permission("product_analysis"))])
async def top_products_trend(
    days: int = Query(30, ge=1, le=90),
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    today = date.today()
    start = today - timedelta(days=days - 1)
    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(today, datetime.max.time())
    paid_statuses = ["paid", "shipped", "completed"]

    # 第一步：按总销售额选 TOP-N 商品
    top_rows = (
        db.query(
            OrderItem.product_id.label("pid"),
            func.coalesce(func.sum(OrderItem.subtotal), 0).label("total_sales"),
            func.coalesce(func.sum(OrderItem.quantity), 0).label("total_qty"),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .filter(
            Order.created_at >= start_dt,
            Order.created_at <= end_dt,
            Order.status.in_(paid_statuses),
        )
        .group_by(OrderItem.product_id)
        .order_by(func.sum(OrderItem.subtotal).desc())
        .limit(limit)
        .all()
    )

    labels = [(start + timedelta(days=i)).isoformat() for i in range(days)]

    if not top_rows:
        return success_response({"period_days": days, "dates": labels, "products": []})

    top_ids = [r.pid for r in top_rows]
    qty_map = {r.pid: int(r.total_qty or 0) for r in top_rows}

    products = {
        p.id: p for p in db.query(Product).filter(Product.id.in_(top_ids)).all()
    }

    # 第二步：按 (day, product_id) GROUP BY 拉日级销量
    daily_rows = (
        db.query(
            func.date(Order.created_at).label("day"),
            OrderItem.product_id.label("pid"),
            func.coalesce(func.sum(OrderItem.quantity), 0).label("qty"),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .filter(
            Order.created_at >= start_dt,
            Order.created_at <= end_dt,
            Order.status.in_(paid_statuses),
            OrderItem.product_id.in_(top_ids),
        )
        .group_by(func.date(Order.created_at), OrderItem.product_id)
        .all()
    )

    by_pid_day: dict = {}
    for r in daily_rows:
        day_iso = r.day.isoformat() if hasattr(r.day, "isoformat") else str(r.day)
        by_pid_day.setdefault(r.pid, {})[day_iso] = int(r.qty or 0)

    products_out = []
    for pid in top_ids:
        p = products.get(pid)
        daily_map = by_pid_day.get(pid, {})
        products_out.append(
            {
                "product_id": pid,
                "product_name": p.product_name if p else f"Product {pid}",
                "category": (p.category.value if p and p.category else None),
                "total_qty": qty_map.get(pid, 0),
                "daily": [daily_map.get(d, 0) for d in labels],
            }
        )

    return success_response(
        {
            "period_days": days,
            "dates": labels,
            "products": products_out,
        }
    )


# 指定日期 + 品类的当日 TOP-N 商品销量
@router.get("/category-daily-top", response_model=dict, dependencies=[Depends(check_module_permission("product_analysis"))])
async def category_daily_top(
    date_str: str = Query(None, alias="date"),
    category: str = Query(None),
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    if date_str:
        try:
            target = date.fromisoformat(date_str)
        except ValueError:
            target = date.today()
    else:
        target = date.today()
    s_dt = datetime.combine(target, datetime.min.time())
    e_dt = datetime.combine(target, datetime.max.time())

    paid_statuses = ["paid", "shipped", "completed"]

    q = (
        db.query(
            OrderItem.product_id.label("pid"),
            func.coalesce(func.sum(OrderItem.subtotal), 0).label("sales"),
            func.coalesce(func.sum(OrderItem.quantity), 0).label("qty"),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .join(Product, Product.id == OrderItem.product_id)
        .filter(
            Order.created_at >= s_dt,
            Order.created_at <= e_dt,
            Order.status.in_(paid_statuses),
        )
    )
    if category:
        q = q.filter(Product.category == category)

    rows = (
        q.group_by(OrderItem.product_id)
        .order_by(func.sum(OrderItem.subtotal).desc())
        .limit(limit)
        .all()
    )

    products = (
        {
            p.id: p
            for p in db.query(Product)
            .filter(Product.id.in_([r.pid for r in rows]))
            .all()
        }
        if rows
        else {}
    )

    data = []
    for r in rows:
        p = products.get(r.pid)
        data.append(
            {
                "product_id": r.pid,
                "product_name": p.product_name if p else f"Product {r.pid}",
                "category": (p.category.value if p and p.category else None),
                "quantity": int(r.qty or 0),
                "sales": float(r.sales or 0),
            }
        )

    return success_response(
        {
            "date": target.isoformat(),
            "category": category,
            "data": data,
        }
    )


# 按品类分析毛利润
@router.get("/profit-analysis", response_model=dict, dependencies=[Depends(check_module_permission("product_analysis"))])
async def profit_analysis(
    date_range: str = Query("last_30_days"),
    start_date: str = Query(None),
    end_date: str = Query(None),
    db: Session = Depends(get_db),
):
    start, end = parse_date_range(date_range, start_date, end_date)

    items = (
        db.query(OrderItem, Order)
        .join(Order, OrderItem.order_id == Order.id)
        .filter(
            Order.created_at >= datetime.combine(start, datetime.min.time()),
            Order.created_at <= datetime.combine(end, datetime.max.time()),
            Order.status.in_(["paid", "shipped", "completed"]),
        )
        .all()
    )

    category_stats = {}
    for item, order in items:
        cat = item.product.category.value if item.product.category else "Unknown"
        if cat not in category_stats:
            category_stats[cat] = {
                "revenue": Decimal(0),
                "cost": Decimal(0),
                "quantity": 0,
            }
        category_stats[cat]["revenue"] += item.subtotal
        category_stats[cat]["cost"] += item.product.cost * item.quantity
        category_stats[cat]["quantity"] += item.quantity

    data = []
    for cat, stats in category_stats.items():
        profit = stats["revenue"] - stats["cost"]
        margin = (profit / stats["revenue"] * 100) if stats["revenue"] > 0 else 0
        data.append(
            {
                "category": cat,
                "revenue": float(stats["revenue"]),
                "cost": float(stats["cost"]),
                "profit": float(profit),
                "profit_margin": round(float(margin), 2),
                "quantity": stats["quantity"],
            }
        )

    return success_response(
        {
            "period": {"start": start.isoformat(), "end": end.isoformat()},
            "data": sorted(data, key=lambda x: x["profit"], reverse=True),
        }
    )
