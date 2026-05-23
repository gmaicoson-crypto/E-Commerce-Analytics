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


# 财务 KPI：收入、各项支出、净利润、利润率
# FinanceRecord 通过订单状态机与 Order 强同步，无需关联订单表查询
@router.get("/kpi", response_model=dict, dependencies=[Depends(check_module_permission("finance_overview"))])
async def finance_kpi(
    date_range: str = Query("today"),
    start_date: str = Query(None),
    end_date: str = Query(None),
    db: Session = Depends(get_db),
):
    start, end = parse_date_range(date_range, start_date, end_date)

    s_dt = datetime.combine(start, datetime.min.time())
    e_dt = datetime.combine(end, datetime.max.time())

    row = (
        db.query(
            func.coalesce(
                func.sum(
                    case(
                        (FinanceRecord.category == "sales_income", FinanceRecord.amount),
                        else_=0,
                    )
                ),
                0,
            ).label("income"),
            func.coalesce(
                func.sum(
                    case(
                        (FinanceRecord.category == "product_cost", FinanceRecord.amount),
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


# 财务按分类汇总（sales_income / product_cost / logistics_cost / ad_cost / refund_out）
@router.get("/by-category", response_model=dict, dependencies=[Depends(check_module_permission("finance_overview"))])
async def finance_by_category(
    date_range: str = Query("today"),
    start_date: str = Query(None),
    end_date: str = Query(None),
    db: Session = Depends(get_db),
):
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


# 财务按收入/支出类型汇总
@router.get("/by-type", response_model=dict, dependencies=[Depends(check_module_permission("finance_overview"))])
async def finance_by_type(
    date_range: str = Query("today"),
    start_date: str = Query(None),
    end_date: str = Query(None),
    db: Session = Depends(get_db),
):
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


# 财务趋势：按天统计收入/支出，缺失日期补零
@router.get("/trend", response_model=dict, dependencies=[Depends(check_module_permission("finance_overview"))])
async def finance_trend(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    today = date.today()
    start = today - timedelta(days=days - 1)
    s_dt = datetime.combine(start, datetime.min.time())
    e_dt = datetime.combine(today, datetime.max.time())

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


# 支出项明细及占比
@router.get("/expense-breakdown", response_model=dict, dependencies=[Depends(check_module_permission("finance_overview"))])
async def expense_breakdown(
    date_range: str = Query("last_30_days"),
    start_date: str = Query(None),
    end_date: str = Query(None),
    db: Session = Depends(get_db),
):
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


# 财务记录列表（分页 + 类型/分类/日期筛选）
@router.get("/records", response_model=dict, dependencies=[Depends(check_module_permission("finance_overview"))])
async def finance_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=10000),
    type_filter: str = Query(None, alias="type"),
    category_filter: str = Query(None, alias="category"),
    date_filter: str = Query(None, alias="date"),
    db: Session = Depends(get_db),
):
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

    # 批量查询本页关联订单号，避免 N+1 查询
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


# 现金流分析：每日利润及累计利润
@router.get("/cash-flow", response_model=dict, dependencies=[Depends(check_module_permission("finance_overview"))])
async def cash_flow(
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
):
    today = date.today()
    start = today - timedelta(days=days)
    s_dt = datetime.combine(start, datetime.min.time())
    e_dt = datetime.combine(today, datetime.max.time())

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
