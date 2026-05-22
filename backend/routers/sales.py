from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
from decimal import Decimal
from database import get_db
from dependencies import check_module_permission
from models import Order, OrderItem, Product
from utils import success_response, parse_date_range, get_prev_period, customer_type_label

router = APIRouter()


@router.get("/overview", response_model=dict)
async def sales_overview(
    date_range: str = Query("today"),
    start_date: str = Query(None),
    end_date: str = Query(None),
    current_user=Depends(check_module_permission("sales_overview")),
    db: Session = Depends(get_db)
):
    """Get sales overview KPIs."""
    start, end = parse_date_range(date_range, start_date, end_date)
    prev_start, prev_end = get_prev_period(start, end)

    # Current period stats
    orders_current = db.query(Order).filter(
        Order.created_at >= datetime.combine(start, datetime.min.time()),
        Order.created_at <= datetime.combine(end, datetime.max.time()),
        Order.status != "refunded"
    ).all()

    total_sales = sum(o.total_amount for o in orders_current) or Decimal(0)
    order_count = len(orders_current)
    avg_order = total_sales / order_count if order_count > 0 else Decimal(0)

    completed_orders = [o for o in orders_current if o.status == "completed"]
    completed_sales = sum(o.total_amount for o in completed_orders) or Decimal(0)

    # Previous period stats for comparison
    orders_prev = db.query(Order).filter(
        Order.created_at >= datetime.combine(prev_start, datetime.min.time()),
        Order.created_at <= datetime.combine(prev_end, datetime.max.time()),
        Order.status != "refunded"
    ).all()

    total_sales_prev = sum(o.total_amount for o in orders_prev) or Decimal(0)
    order_count_prev = len(orders_prev)

    # Calculate change rates
    sales_change = ((total_sales - total_sales_prev) / total_sales_prev * 100) if total_sales_prev else 0
    order_change = ((order_count - order_count_prev) / order_count_prev * 100) if order_count_prev else 0

    return success_response({
        "period": {
            "start": start.isoformat(),
            "end": end.isoformat()
        },
        "total_sales": float(total_sales),
        "total_sales_change": round(float(sales_change), 2),
        "order_count": order_count,
        "order_count_change": round(float(order_change), 2),
        "avg_order_value": float(avg_order),
        "completed_sales": float(completed_sales),
        "completed_order_count": len(completed_orders)
    })


@router.get("/trend", response_model=dict)
async def sales_trend(
    days: int = Query(7, ge=1, le=90),
    current_user=Depends(check_module_permission("sales_overview")),
    db: Session = Depends(get_db)
):
    """Get sales trend data - 单条 SQL GROUP BY DATE,补齐缺失日。"""
    today = date.today()
    start = today - timedelta(days=days - 1)  # 包含今天:start..today 共 days 天

    rows = (
        db.query(
            func.date(Order.created_at).label("day"),
            func.coalesce(func.sum(Order.total_amount), 0).label("sales"),
            func.count(Order.id).label("order_count"),
        )
        .filter(
            Order.created_at >= datetime.combine(start, datetime.min.time()),
            Order.created_at <= datetime.combine(today, datetime.max.time()),
            Order.status.in_(["paid", "shipped", "completed"]),
        )
        .group_by(func.date(Order.created_at))
        .all()
    )

    # 用聚合结果建索引,然后按天补齐(没有订单的日子返回 0)
    by_day = {r.day.isoformat() if hasattr(r.day, "isoformat") else str(r.day): r for r in rows}
    trend_data = []
    for i in range(days):
        day_iso = (start + timedelta(days=i)).isoformat()
        r = by_day.get(day_iso)
        sales = float(r.sales) if r else 0.0
        cnt = int(r.order_count) if r else 0
        trend_data.append({
            "date": day_iso,
            "sales": sales,
            "order_count": cnt,
            "avg_order_value": (sales / cnt) if cnt > 0 else 0,
        })

    return success_response({"period_days": days, "data": trend_data})


@router.get("/by-category", response_model=dict)
async def sales_by_category(
    date_range: str = Query("today"),
    start_date: str = Query(None),
    end_date: str = Query(None),
    current_user=Depends(check_module_permission("sales_overview")),
    db: Session = Depends(get_db)
):
    """Get sales breakdown by product category - 单条 SQL GROUP BY."""
    start, end = parse_date_range(date_range, start_date, end_date)

    rows = (
        db.query(
            Product.category.label("category"),
            func.coalesce(func.sum(OrderItem.subtotal), 0).label("sales"),
            func.coalesce(func.sum(OrderItem.quantity), 0).label("quantity"),
            func.count(func.distinct(Order.id)).label("order_count"),
        )
        .join(OrderItem, OrderItem.product_id == Product.id)
        .join(Order, Order.id == OrderItem.order_id)
        .filter(
            Order.created_at >= datetime.combine(start, datetime.min.time()),
            Order.created_at <= datetime.combine(end, datetime.max.time()),
            Order.status.in_(["paid", "shipped", "completed"]),
        )
        .group_by(Product.category)
        .order_by(func.sum(OrderItem.subtotal).desc())
        .all()
    )

    data = [
        {
            "category": r.category.value if hasattr(r.category, "value") else r.category,
            "sales": float(r.sales),
            "quantity": int(r.quantity),
            "order_count": int(r.order_count),
            "avg_price": float(r.sales / r.quantity) if r.quantity else 0,
        }
        for r in rows
    ]

    return success_response({
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "total_categories": len(data),
        "data": data,
    })


@router.get("/by-customer-type", response_model=dict)
async def sales_by_customer_type(
    date_range: str = Query("today"),
    start_date: str = Query(None),
    end_date: str = Query(None),
    current_user=Depends(check_module_permission("sales_overview")),
    db: Session = Depends(get_db)
):
    """Get sales breakdown by customer type."""
    start, end = parse_date_range(date_range, start_date, end_date)

    orders = db.query(Order).filter(
        Order.created_at >= datetime.combine(start, datetime.min.time()),
        Order.created_at <= datetime.combine(end, datetime.max.time()),
        Order.status.in_(["paid", "shipped", "completed"])
    ).all()

    type_sales = {}
    for order in orders:
        customer = order.customer
        if customer:
            # 改用 registered_at 实时判定:注册 ≤ 30 天为 new,> 30 天为 returning
            ctype = customer_type_label(customer.registered_at)
            if ctype not in type_sales:
                type_sales[ctype] = {"sales": Decimal(0), "order_count": 0}
            type_sales[ctype]["sales"] += order.total_amount
            type_sales[ctype]["order_count"] += 1

    data = [
        {
            "customer_type": ctype,
            "sales": float(stats["sales"]),
            "order_count": stats["order_count"],
            "avg_order_value": float(stats["sales"] / stats["order_count"]) if stats["order_count"] > 0 else 0
        }
        for ctype, stats in type_sales.items()
    ]

    return success_response({
        "period": {
            "start": start.isoformat(),
            "end": end.isoformat()
        },
        "data": data
    })


@router.get("/top-products", response_model=dict)
async def top_products(
    date_range: str = Query("today"),
    start_date: str = Query(None),
    end_date: str = Query(None),
    limit: int = Query(10, ge=1, le=100),
    current_user=Depends(check_module_permission("sales_overview")),
    db: Session = Depends(get_db)
):
    """Get top selling products."""
    start, end = parse_date_range(date_range, start_date, end_date)

    items = db.query(OrderItem, Order).join(
        Order, OrderItem.order_id == Order.id
    ).filter(
        Order.created_at >= datetime.combine(start, datetime.min.time()),
        Order.created_at <= datetime.combine(end, datetime.max.time()),
        Order.status.in_(["paid", "shipped", "completed"])
    ).all()

    product_stats = {}
    for item, order in items:
        pid = item.product_id
        if pid not in product_stats:
            product_stats[pid] = {
                "product_name": item.product.product_name,
                "category": item.product.category.value if item.product.category else "Unknown",
                "quantity": 0,
                "sales": Decimal(0)
            }
        product_stats[pid]["quantity"] += item.quantity
        product_stats[pid]["sales"] += item.subtotal

    data = [
        {
            "product_id": pid,
            "product_name": stats["product_name"],
            "category": stats["category"],
            "quantity": stats["quantity"],
            "sales": float(stats["sales"]),
            "avg_price": float(stats["sales"] / stats["quantity"]) if stats["quantity"] > 0 else 0
        }
        for pid, stats in sorted(product_stats.items(), key=lambda x: x[1]["sales"], reverse=True)[:limit]
    ]

    return success_response({
        "period": {
            "start": start.isoformat(),
            "end": end.isoformat()
        },
        "data": data
    })
