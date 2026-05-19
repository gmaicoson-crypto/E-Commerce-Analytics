from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
from decimal import Decimal
from database import get_db
from dependencies import check_module_permission
from models import FinanceRecord, Order, OrderItem, Product
from utils import success_response, parse_date_range

router = APIRouter()


@router.get("/kpi", response_model=dict)
async def finance_kpi(
    date_range: str = Query("today"),
    start_date: str = Query(None),
    end_date: str = Query(None),
    current_user=Depends(check_module_permission("finance_overview")),
    db: Session = Depends(get_db)
):
    """Get finance KPI overview."""
    start, end = parse_date_range(date_range, start_date, end_date)

    records = db.query(FinanceRecord).filter(
        FinanceRecord.recorded_at >= datetime.combine(start, datetime.min.time()),
        FinanceRecord.recorded_at <= datetime.combine(end, datetime.max.time())
    ).all()

    income = sum(r.amount for r in records if r.type.value == "income") or Decimal(0)

    # 新规则:总支出 = 物流成本 + 广告成本 + 已完成订单的商品成本
    #   - 物流/广告:来自 finance_records 表(_add_completed_finance 写入)
    #   - 商品成本:SUM(OrderItem.quantity × Product.cost) WHERE Order.status='completed'
    logistics_ad = sum(
        r.amount for r in records
        if r.type.value == "expense" and r.category.value in ("logistics_cost", "ad_cost")
    ) or Decimal(0)

    product_cost_raw = (
        db.query(func.coalesce(func.sum(OrderItem.quantity * Product.cost), 0))
        .join(Order, Order.id == OrderItem.order_id)
        .join(Product, Product.id == OrderItem.product_id)
        .filter(
            Order.status == "completed",
            Order.created_at >= datetime.combine(start, datetime.min.time()),
            Order.created_at <= datetime.combine(end, datetime.max.time()),
        )
        .scalar()
    ) or 0
    product_cost = Decimal(str(product_cost_raw))

    expense = logistics_ad + product_cost
    profit = income - expense

    profit_margin = (profit / income * 100) if income > 0 else 0

    # Get order count for context
    orders = db.query(Order).filter(
        Order.created_at >= datetime.combine(start, datetime.min.time()),
        Order.created_at <= datetime.combine(end, datetime.max.time()),
        Order.status.in_(["paid", "shipped", "completed"])
    ).count()

    return success_response({
        "period": {
            "start": start.isoformat(),
            "end": end.isoformat()
        },
        "total_income": float(income),
        "total_expense": float(expense),
        "net_profit": float(profit),
        "profit_margin": round(float(profit_margin), 2),
        "order_count": orders,
        "profit_per_order": float(profit / orders) if orders > 0 else 0
    })


@router.get("/by-category", response_model=dict)
async def finance_by_category(
    date_range: str = Query("today"),
    start_date: str = Query(None),
    end_date: str = Query(None),
    current_user=Depends(check_module_permission("finance_overview")),
    db: Session = Depends(get_db)
):
    """Get finance breakdown by category."""
    start, end = parse_date_range(date_range, start_date, end_date)

    records = db.query(FinanceRecord).filter(
        FinanceRecord.recorded_at >= datetime.combine(start, datetime.min.time()),
        FinanceRecord.recorded_at <= datetime.combine(end, datetime.max.time())
    ).all()

    category_stats = {}
    for record in records:
        cat = record.category.value if record.category else "Unknown"
        if cat not in category_stats:
            category_stats[cat] = Decimal(0)
        category_stats[cat] += record.amount

    data = [
        {
            "category": cat,
            "amount": float(amount)
        }
        for cat, amount in sorted(category_stats.items(), key=lambda x: x[1], reverse=True)
    ]

    return success_response({
        "period": {
            "start": start.isoformat(),
            "end": end.isoformat()
        },
        "data": data
    })


@router.get("/by-type", response_model=dict)
async def finance_by_type(
    date_range: str = Query("today"),
    start_date: str = Query(None),
    end_date: str = Query(None),
    current_user=Depends(check_module_permission("finance_overview")),
    db: Session = Depends(get_db)
):
    """Get finance breakdown by income/expense."""
    start, end = parse_date_range(date_range, start_date, end_date)

    records = db.query(FinanceRecord).filter(
        FinanceRecord.recorded_at >= datetime.combine(start, datetime.min.time()),
        FinanceRecord.recorded_at <= datetime.combine(end, datetime.max.time())
    ).all()

    type_stats = {}
    for record in records:
        rtype = record.type.value if record.type else "Unknown"
        if rtype not in type_stats:
            type_stats[rtype] = Decimal(0)
        type_stats[rtype] += record.amount

    data = [
        {
            "type": rtype,
            "amount": float(amount)
        }
        for rtype, amount in type_stats.items()
    ]

    income = type_stats.get("income", Decimal(0))
    expense = type_stats.get("expense", Decimal(0))

    return success_response({
        "period": {
            "start": start.isoformat(),
            "end": end.isoformat()
        },
        "income": float(income),
        "expense": float(expense),
        "net_profit": float(income - expense),
        "data": data
    })


@router.get("/trend", response_model=dict)
async def finance_trend(
    days: int = Query(7, ge=1, le=90),
    current_user=Depends(check_module_permission("finance_overview")),
    db: Session = Depends(get_db)
):
    """Get finance trend over time."""
    today = date.today()
    start = today - timedelta(days=days - 1)  # 包含今天:共 days 天

    trend_data = []
    for i in range(days):
        day = start + timedelta(days=i)
        records = db.query(FinanceRecord).filter(
            FinanceRecord.recorded_at >= datetime.combine(day, datetime.min.time()),
            FinanceRecord.recorded_at <= datetime.combine(day, datetime.max.time())
        ).all()

        income = sum(r.amount for r in records if r.type.value == "income") or Decimal(0)
        expense = sum(r.amount for r in records if r.type.value == "expense") or Decimal(0)

        trend_data.append({
            "date": day.isoformat(),
            "income": float(income),
            "expense": float(expense),
            "profit": float(income - expense)
        })

    return success_response({
        "period_days": days,
        "data": trend_data
    })


@router.get("/expense-breakdown", response_model=dict)
async def expense_breakdown(
    date_range: str = Query("last_30_days"),
    start_date: str = Query(None),
    end_date: str = Query(None),
    current_user=Depends(check_module_permission("finance_overview")),
    db: Session = Depends(get_db)
):
    """Get expense breakdown by category."""
    start, end = parse_date_range(date_range, start_date, end_date)

    records = db.query(FinanceRecord).filter(
        FinanceRecord.recorded_at >= datetime.combine(start, datetime.min.time()),
        FinanceRecord.recorded_at <= datetime.combine(end, datetime.max.time()),
        FinanceRecord.type.in_(["expense"])
    ).all()

    category_stats = {}
    for record in records:
        cat = record.category.value if record.category else "Unknown"
        if cat not in category_stats:
            category_stats[cat] = Decimal(0)
        category_stats[cat] += record.amount

    data = [
        {
            "category": cat,
            "amount": float(amount),
            "percentage": round((amount / sum(category_stats.values()) * 100), 2) if category_stats else 0
        }
        for cat, amount in sorted(category_stats.items(), key=lambda x: x[1], reverse=True)
    ]

    return success_response({
        "period": {
            "start": start.isoformat(),
            "end": end.isoformat()
        },
        "total_expense": float(sum(category_stats.values()) or 0),
        "data": data
    })


@router.get("/records", response_model=dict)
async def finance_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=10000),
    type_filter: str = Query(None, alias="type"),
    category_filter: str = Query(None, alias="category"),
    current_user=Depends(check_module_permission("finance_overview")),
    db: Session = Depends(get_db)
):
    """Get paginated finance records."""
    query = db.query(FinanceRecord)
    if type_filter:
        query = query.filter(FinanceRecord.type == type_filter)
    if category_filter:
        query = query.filter(FinanceRecord.category == category_filter)

    total = query.count()
    records = query.order_by(FinanceRecord.recorded_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    data = []
    for r in records:
        order_no = None
        if r.related_order_id:
            order = db.query(Order).filter(Order.id == r.related_order_id).first()
            order_no = order.order_no if order else None

        data.append({
            "id": r.id,
            "type": r.type.value if r.type else "Unknown",
            "category": r.category.value if r.category else "Unknown",
            "amount": float(r.amount),
            "order_no": order_no,
            "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None
        })

    return success_response({
        "data": data,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size
        }
    })


@router.get("/cash-flow", response_model=dict)
async def cash_flow(
    days: int = Query(30, ge=1, le=90),
    current_user=Depends(check_module_permission("finance_overview")),
    db: Session = Depends(get_db)
):
    """Get cash flow analysis."""
    today = date.today()
    start = today - timedelta(days=days)

    cumulative_profit = Decimal(0)
    cash_flow_data = []

    for i in range(days):
        day = start + timedelta(days=i)
        records = db.query(FinanceRecord).filter(
            FinanceRecord.recorded_at >= datetime.combine(day, datetime.min.time()),
            FinanceRecord.recorded_at <= datetime.combine(day, datetime.max.time())
        ).all()

        income = sum(r.amount for r in records if r.type.value == "income") or Decimal(0)
        expense = sum(r.amount for r in records if r.type.value == "expense") or Decimal(0)
        daily_profit = income - expense
        cumulative_profit += daily_profit

        cash_flow_data.append({
            "date": day.isoformat(),
            "daily_profit": float(daily_profit),
            "cumulative_profit": float(cumulative_profit)
        })

    return success_response({
        "period_days": days,
        "data": cash_flow_data
    })
