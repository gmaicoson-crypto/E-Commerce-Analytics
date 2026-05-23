from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, case
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Dict
from database import get_db
from dependencies import check_module_permission
from models import FinanceRecord, Order
from utils import success_response, parse_date_range

router = APIRouter()


@router.get("/kpi", response_model=dict, dependencies=[Depends(check_module_permission("finance_overview"))])
async def finance_kpi(
    date_range: str = Query("today"),
    start_date: str = Query(None),
    end_date: str = Query(None),
    db: Session = Depends(get_db),
):
    """Get finance KPI overview."""
    start, end = parse_date_range(date_range, start_date, end_date)

    s_dt = datetime.combine(start, datetime.min.time())
    e_dt = datetime.combine(end, datetime.max.time())

    # 状态机已保证 FinanceRecord 与 Order 强同步:
    #   - paid     → 写入 sales_income + product_cost + ad_cost
    #   - shipped  → 写入 logistics_cost
    #   - refunded → 删除该订单全部 finance
    # 因此一条 SQL GROUP BY + 条件聚合即可拿齐所有 KPI。
    row = (
        db.query(
            func.coalesce(
                func.sum(
                    case(
                        (
                            FinanceRecord.category == "sales_income",
                            FinanceRecord.amount,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("income"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            FinanceRecord.category == "product_cost",
                            FinanceRecord.amount,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("product_cost"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            FinanceRecord.category == "logistics_cost",
                            FinanceRecord.amount,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("logistics_cost"),
            func.coalesce(
                func.sum(
                    case(
                        (FinanceRecord.category == "ad_cost", FinanceRecord.amount),
                        else_=0,
                    )
                ),
                0,
            ).label("ad_cost"),
            func.coalesce(
                func.sum(
                    case(
                        (FinanceRecord.category == "refund_out", FinanceRecord.amount),
                        else_=0,
                    )
                ),
                0,
            ).label("refund_out"),
            func.count(
                func.distinct(
                    case(
                        (
                            FinanceRecord.category == "sales_income",
                            FinanceRecord.related_order_id,
                        ),
                        else_=None,
                    )
                )
            ).label("orders"),
        )
        .filter(FinanceRecord.recorded_at >= s_dt, FinanceRecord.recorded_at <= e_dt)
        .one()
    )
    income = Decimal(str(row.income))
    product_cost = Decimal(str(row.product_cost))
    logistics_cost = Decimal(str(row.logistics_cost))
    ad_cost = Decimal(str(row.ad_cost))
    refund_out = Decimal(str(row.refund_out))
    orders = int(row.orders or 0)

    expense = product_cost + logistics_cost + ad_cost + refund_out
    profit = income - expense
    profit_margin = (profit / income * 100) if income > 0 else 0

    return success_response(
        {
            "period": {"start": start.isoformat(), "end": end.isoformat()},
            "total_income": float(income),
            "total_expense": float(expense),
            "net_profit": float(profit),
            "profit_margin": round(float(profit_margin), 2),
            "order_count": orders,
            "profit_per_order": float(profit / orders) if orders > 0 else 0,
        }
    )


@router.get("/by-category", response_model=dict, dependencies=[Depends(check_module_permission("finance_overview"))])
async def finance_by_category(
    date_range: str = Query("today"),
    start_date: str = Query(None),
    end_date: str = Query(None),
    db: Session = Depends(get_db),
):
    """Get finance breakdown by category."""
    start, end = parse_date_range(date_range, start_date, end_date)

    records = (
        db.query(FinanceRecord)
        .filter(
            FinanceRecord.recorded_at >= datetime.combine(start, datetime.min.time()),
            FinanceRecord.recorded_at <= datetime.combine(end, datetime.max.time()),
        )
        .all()
    )

    category_stats = {}
    for record in records:
        cat = record.category.value if record.category else "Unknown"
        if cat not in category_stats:
            category_stats[cat] = Decimal(0)
        category_stats[cat] += record.amount

    data = [
        {"category": cat, "amount": float(amount)}
        for cat, amount in sorted(
            category_stats.items(), key=lambda x: x[1], reverse=True
        )
    ]

    return success_response(
        {"period": {"start": start.isoformat(), "end": end.isoformat()}, "data": data}
    )


@router.get("/by-type", response_model=dict, dependencies=[Depends(check_module_permission("finance_overview"))])
async def finance_by_type(
    date_range: str = Query("today"),
    start_date: str = Query(None),
    end_date: str = Query(None),
    db: Session = Depends(get_db),
):
    """Get finance breakdown by income/expense."""
    start, end = parse_date_range(date_range, start_date, end_date)

    records = (
        db.query(FinanceRecord)
        .filter(
            FinanceRecord.recorded_at >= datetime.combine(start, datetime.min.time()),
            FinanceRecord.recorded_at <= datetime.combine(end, datetime.max.time()),
        )
        .all()
    )

    type_stats = {}
    for record in records:
        rtype = record.type.value if record.type else "Unknown"
        if rtype not in type_stats:
            type_stats[rtype] = Decimal(0)
        type_stats[rtype] += record.amount

    data = [
        {"type": rtype, "amount": float(amount)} for rtype, amount in type_stats.items()
    ]

    income = type_stats.get("income", Decimal(0))
    expense = type_stats.get("expense", Decimal(0))

    return success_response(
        {
            "period": {"start": start.isoformat(), "end": end.isoformat()},
            "income": float(income),
            "expense": float(expense),
            "net_profit": float(income - expense),
            "data": data,
        }
    )


@router.get("/trend", response_model=dict, dependencies=[Depends(check_module_permission("finance_overview"))])
async def finance_trend(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    """Get finance trend over time."""
    today = date.today()
    start = today - timedelta(days=days - 1)  # 包含今天:共 days 天
    s_dt = datetime.combine(start, datetime.min.time())
    e_dt = datetime.combine(today, datetime.max.time())

    # 单条 SQL:按 DATE(recorded_at) 分组,一次拿齐所有天的 income / expense
    day_col = func.date(FinanceRecord.recorded_at).label("d")
    rows = (
        db.query(
            day_col,
            func.coalesce(
                func.sum(
                    case(
                        (FinanceRecord.type == "income", FinanceRecord.amount), else_=0
                    )
                ),
                0,
            ).label("income"),
            func.coalesce(
                func.sum(
                    case(
                        (FinanceRecord.type == "expense", FinanceRecord.amount), else_=0
                    )
                ),
                0,
            ).label("expense"),
        )
        .filter(FinanceRecord.recorded_at >= s_dt, FinanceRecord.recorded_at <= e_dt)
        .group_by(day_col)
        .all()
    )
    by_day = {str(r.d): (Decimal(str(r.income)), Decimal(str(r.expense))) for r in rows}

    trend_data = []
    for i in range(days):
        day = start + timedelta(days=i)
        income, expense = by_day.get(day.isoformat(), (Decimal(0), Decimal(0)))
        trend_data.append(
            {
                "date": day.isoformat(),
                "income": float(income),
                "expense": float(expense),
                "profit": float(income - expense),
            }
        )

    return success_response({"period_days": days, "data": trend_data})


@router.get("/expense-breakdown", response_model=dict, dependencies=[Depends(check_module_permission("finance_overview"))])
async def expense_breakdown(
    date_range: str = Query("last_30_days"),
    start_date: str = Query(None),
    end_date: str = Query(None),
    db: Session = Depends(get_db),
):
    """Get expense breakdown by category.

    与 /kpi 同口径,从 FinanceRecord 表 GROUP BY category 一次取齐
    (状态机已保证它和 Order 强同步)。
    """
    start, end = parse_date_range(date_range, start_date, end_date)
    s_dt = datetime.combine(start, datetime.min.time())
    e_dt = datetime.combine(end, datetime.max.time())

    rows = (
        db.query(
            FinanceRecord.category,
            func.coalesce(func.sum(FinanceRecord.amount), 0).label("amt"),
        )
        .filter(
            FinanceRecord.recorded_at >= s_dt,
            FinanceRecord.recorded_at <= e_dt,
            FinanceRecord.type == "expense",
        )
        .group_by(FinanceRecord.category)
        .all()
    )
    category_amounts: Dict[str, Decimal] = {
        (r.category.value if hasattr(r.category, "value") else r.category): Decimal(
            str(r.amt)
        )
        for r in rows
        if Decimal(str(r.amt)) > 0
    }
    total = sum(category_amounts.values()) or Decimal(0)

    data = [
        {
            "category": cat,
            "amount": float(amount),
            "percentage": round(float(amount / total * 100), 2) if total > 0 else 0,
        }
        for cat, amount in sorted(
            category_amounts.items(), key=lambda x: x[1], reverse=True
        )
    ]

    return success_response(
        {
            "period": {"start": start.isoformat(), "end": end.isoformat()},
            "total_expense": float(total),
            "data": data,
        }
    )


@router.get("/records", response_model=dict, dependencies=[Depends(check_module_permission("finance_overview"))])
async def finance_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=10000),
    type_filter: str = Query(None, alias="type"),
    category_filter: str = Query(None, alias="category"),
    date_filter: str = Query(None, alias="date"),  # 'YYYY-MM-DD' 仅返回当日记录
    db: Session = Depends(get_db),
):
    """Get paginated finance records."""
    query = db.query(FinanceRecord)
    if type_filter:
        query = query.filter(FinanceRecord.type == type_filter)
    if category_filter:
        query = query.filter(FinanceRecord.category == category_filter)
    if date_filter:
        try:
            target = date.fromisoformat(date_filter)
            s_dt = datetime.combine(target, datetime.min.time())
            e_dt = datetime.combine(target, datetime.max.time())
            query = query.filter(
                FinanceRecord.recorded_at >= s_dt, FinanceRecord.recorded_at <= e_dt
            )
        except ValueError:
            pass

    total = query.count()
    records = (
        query.order_by(FinanceRecord.recorded_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # 一次性把本页所有 related_order_id 对应的 order_no 取出来,避免 N+1 查询
    order_ids = {r.related_order_id for r in records if r.related_order_id}
    order_no_map: Dict[int, str] = {}
    if order_ids:
        order_no_map = {
            o.id: o.order_no
            for o in db.query(Order.id, Order.order_no)
            .filter(Order.id.in_(order_ids))
            .all()
        }

    data = []
    for r in records:
        data.append(
            {
                "id": r.id,
                "type": r.type.value if r.type else "Unknown",
                "category": r.category.value if r.category else "Unknown",
                "amount": float(r.amount),
                "order_no": (
                    order_no_map.get(r.related_order_id) if r.related_order_id else None
                ),
                "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None,
            }
        )

    return success_response(
        {
            "data": data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size,
            },
        }
    )


@router.get("/cash-flow", response_model=dict, dependencies=[Depends(check_module_permission("finance_overview"))])
async def cash_flow(
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
):
    """Get cash flow analysis."""
    today = date.today()
    start = today - timedelta(days=days)
    s_dt = datetime.combine(start, datetime.min.time())
    e_dt = datetime.combine(today, datetime.max.time())

    # 单条 SQL:按 DATE(recorded_at) 分组,一次拿齐所有天的 income / expense
    day_col = func.date(FinanceRecord.recorded_at).label("d")
    rows = (
        db.query(
            day_col,
            func.coalesce(
                func.sum(
                    case(
                        (FinanceRecord.type == "income", FinanceRecord.amount), else_=0
                    )
                ),
                0,
            ).label("income"),
            func.coalesce(
                func.sum(
                    case(
                        (FinanceRecord.type == "expense", FinanceRecord.amount), else_=0
                    )
                ),
                0,
            ).label("expense"),
        )
        .filter(FinanceRecord.recorded_at >= s_dt, FinanceRecord.recorded_at <= e_dt)
        .group_by(day_col)
        .all()
    )
    by_day = {str(r.d): (Decimal(str(r.income)), Decimal(str(r.expense))) for r in rows}

    cumulative_profit = Decimal(0)
    cash_flow_data = []
    for i in range(days):
        day = start + timedelta(days=i)
        income, expense = by_day.get(day.isoformat(), (Decimal(0), Decimal(0)))
        daily_profit = income - expense
        cumulative_profit += daily_profit
        cash_flow_data.append(
            {
                "date": day.isoformat(),
                "daily_profit": float(daily_profit),
                "cumulative_profit": float(cumulative_profit),
            }
        )

    return success_response({"period_days": days, "data": cash_flow_data})
