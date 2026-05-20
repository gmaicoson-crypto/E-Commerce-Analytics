from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
from decimal import Decimal
from database import get_db
from dependencies import check_module_permission, get_current_user
from models import Product, Order, OrderItem, Order
from utils import success_response, parse_date_range

router = APIRouter()


@router.get("/overview", response_model=dict)
async def products_overview(
    current_user=Depends(check_module_permission("product_analysis")),
    db: Session = Depends(get_db)
):
    """Get product overview statistics."""
    total_products = db.query(Product).count()
    on_sale = db.query(Product).filter(Product.status == "on_sale").count()
    off_sale = db.query(Product).filter(Product.status == "off_sale").count()
    low_stock = db.query(Product).filter(
        Product.stock < Product.low_stock_threshold
    ).count()

    total_stock = db.query(func.sum(Product.stock)).scalar() or 0
    total_value = db.query(
        func.sum(Product.stock * Product.price)
    ).scalar() or Decimal(0)

    return success_response({
        "total_products": total_products,
        "on_sale": on_sale,
        "off_sale": off_sale,
        "low_stock_count": low_stock,
        "total_stock": int(total_stock),
        "total_inventory_value": float(total_value)
    })


@router.get("/by-category", response_model=dict)
async def products_by_category(
    current_user=Depends(check_module_permission("product_analysis")),
    db: Session = Depends(get_db)
):
    """Get products grouped by category - 单条 SQL GROUP BY。"""
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
            "category": r.category.value if hasattr(r.category, "value") else r.category,
            "count": int(r.count),
            "on_sale": int(r.on_sale or 0),
            "avg_price": float(r.avg_price),
            "avg_cost": float(r.avg_cost),
            "total_stock": int(r.total_stock),
        }
        for r in rows
    ]

    return success_response(data)


@router.get("/low-stock", response_model=dict)
async def low_stock_products(
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(check_module_permission("product_analysis")),
    db: Session = Depends(get_db)
):
    """Get products with low stock."""
    products = db.query(Product).filter(
        Product.stock < Product.low_stock_threshold
    ).order_by(Product.stock.asc()).limit(limit).all()

    data = [
        {
            "id": p.id,
            "product_name": p.product_name,
            "category": p.category.value if p.category else "Unknown",
            "stock": p.stock,
            "low_stock_threshold": p.low_stock_threshold,
            "price": float(p.price),
            "status": p.status
        }
        for p in products
    ]

    return success_response({
        "count": len(data),
        "data": data
    })


@router.get("/highlights", response_model=dict)
async def product_highlights(
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(8, ge=1, le=20),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """横幅滚动用的轻量热卖榜 —— 任何登录用户可见,不查模块权限。"""
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
    return success_response({
        "data": [
            {
                "product_name": r.product_name,
                "category": r.category.value if hasattr(r.category, "value") else r.category,
                "quantity_sold": int(r.quantity_sold),
                "sales": float(r.sales),
            }
            for r in rows
        ]
    })


@router.get("/performance", response_model=dict)
async def product_performance(
    date_range: str = Query("last_7_days"),
    start_date: str = Query(None),
    end_date: str = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(check_module_permission("product_analysis")),
    db: Session = Depends(get_db)
):
    """Get product sales performance - 单条 SQL GROUP BY product_id。"""
    start, end = parse_date_range(date_range, start_date, end_date)

    rows = (
        db.query(
            Product.id.label("product_id"),
            Product.product_name.label("product_name"),
            Product.category.label("category"),
            Product.price.label("price"),
            func.coalesce(func.sum(OrderItem.quantity), 0).label("quantity_sold"),
            func.coalesce(func.sum(OrderItem.subtotal), 0).label("sales"),
            func.coalesce(func.sum(OrderItem.subtotal - Product.cost * OrderItem.quantity), 0).label("profit"),
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
            "category": r.category.value if hasattr(r.category, "value") else r.category,
            "price": float(r.price),
            "quantity_sold": int(r.quantity_sold),
            "sales": float(r.sales),
            "profit": float(r.profit),
            "profit_margin": float((r.profit / r.sales) * 100) if r.sales else 0,
        }
        for r in rows
    ]

    return success_response({
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "data": data,
    })


@router.get("/top-trend", response_model=dict)
async def top_products_trend(
    days: int = Query(30, ge=1, le=90),
    limit: int = Query(5, ge=1, le=20),
    current_user=Depends(check_module_permission("product_analysis")),
    db: Session = Depends(get_db),
):
    """TOP-N 商品的近 N 天**真实**日销量曲线(含今天)。

    返回 {dates: ["YYYY-MM-DD" × days], products: [{product_id, product_name,
    category, total_qty, daily: [int × days]}]}
    """
    today = date.today()
    start = today - timedelta(days=days - 1)
    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(today, datetime.max.time())
    paid_statuses = ["paid", "shipped", "completed"]

    # 1) 先按总销售额选 TOP-N 商品 ID
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

    # 2) 拿商品基础信息
    products = {
        p.id: p for p in db.query(Product).filter(Product.id.in_(top_ids)).all()
    }

    # 3) 单条 SQL:按 (day, product_id) GROUP BY 拉日级销量
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
        products_out.append({
            "product_id": pid,
            "product_name": p.product_name if p else f"Product {pid}",
            "category": (p.category.value if p and p.category else None),
            "total_qty": qty_map.get(pid, 0),
            "daily": [daily_map.get(d, 0) for d in labels],
        })

    return success_response({
        "period_days": days,
        "dates": labels,
        "products": products_out,
    })


@router.get("/category-daily-top", response_model=dict)
async def category_daily_top(
    date_str: str = Query(None, alias="date"),  # 'YYYY-MM-DD',缺省 = 今天
    category: str = Query(None),                # 中文品类名:服装/电子/食品/家居/美妆
    limit: int = Query(5, ge=1, le=20),
    current_user=Depends(check_module_permission("product_analysis")),
    db: Session = Depends(get_db),
):
    """指定日期 + 指定品类的当日 TOP-N 商品销量(按销售额排序)。"""
    # 日期解析
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

    products = {
        p.id: p for p in db.query(Product).filter(Product.id.in_([r.pid for r in rows])).all()
    } if rows else {}

    data = []
    for r in rows:
        p = products.get(r.pid)
        data.append({
            "product_id": r.pid,
            "product_name": p.product_name if p else f"Product {r.pid}",
            "category": (p.category.value if p and p.category else None),
            "quantity": int(r.qty or 0),
            "sales": float(r.sales or 0),
        })

    return success_response({
        "date": target.isoformat(),
        "category": category,
        "data": data,
    })


@router.get("/profit-analysis", response_model=dict)
async def profit_analysis(
    date_range: str = Query("last_30_days"),
    start_date: str = Query(None),
    end_date: str = Query(None),
    current_user=Depends(check_module_permission("product_analysis")),
    db: Session = Depends(get_db)
):
    """Get profit analysis by category."""
    start, end = parse_date_range(date_range, start_date, end_date)

    items = db.query(OrderItem, Order).join(
        Order, OrderItem.order_id == Order.id
    ).filter(
        Order.created_at >= datetime.combine(start, datetime.min.time()),
        Order.created_at <= datetime.combine(end, datetime.max.time()),
        Order.status.in_(["paid", "shipped", "completed"])
    ).all()

    category_stats = {}
    for item, order in items:
        cat = item.product.category.value if item.product.category else "Unknown"
        if cat not in category_stats:
            category_stats[cat] = {
                "revenue": Decimal(0),
                "cost": Decimal(0),
                "quantity": 0
            }
        category_stats[cat]["revenue"] += item.subtotal
        category_stats[cat]["cost"] += item.product.cost * item.quantity
        category_stats[cat]["quantity"] += item.quantity

    data = []
    for cat, stats in category_stats.items():
        profit = stats["revenue"] - stats["cost"]
        margin = (profit / stats["revenue"] * 100) if stats["revenue"] > 0 else 0
        data.append({
            "category": cat,
            "revenue": float(stats["revenue"]),
            "cost": float(stats["cost"]),
            "profit": float(profit),
            "profit_margin": round(float(margin), 2),
            "quantity": stats["quantity"]
        })

    return success_response({
        "period": {
            "start": start.isoformat(),
            "end": end.isoformat()
        },
        "data": sorted(data, key=lambda x: x["profit"], reverse=True)
    })
