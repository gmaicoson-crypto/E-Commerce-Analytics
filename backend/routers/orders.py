from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
from decimal import Decimal
from database import get_db
from dependencies import check_module_permission
from models import Order, Refund
from utils import success_response, parse_date_range

router = APIRouter()


# 订单概览：6 种状态的数量与金额汇总
@router.get("/overview", response_model=dict, dependencies=[Depends(check_module_permission("order_analysis"))])
async def orders_overview(
    date_range: str = Query("today"),
    start_date: str = Query(None),
    end_date: str = Query(None),
    db: Session = Depends(get_db),
):
    start, end = parse_date_range(date_range, start_date, end_date)

    orders = (
        db.query(Order)
        .filter(
            Order.created_at >= datetime.combine(start, datetime.min.time()),
            Order.created_at <= datetime.combine(end, datetime.max.time()),
        )
        .all()
    )

    total_orders = len(orders)
    by_status: dict[str, tuple[int, Decimal]] = {
        s: (0, Decimal(0))
        for s in ("pending", "paid", "shipped", "completed", "cancelled", "refunded")
    }
    for o in orders:
        s = o.status.value if hasattr(o.status, "value") else o.status
        if s in by_status:
            cnt, amt = by_status[s]
            by_status[s] = (cnt + 1, amt + (o.total_amount or Decimal(0)))

    total_amount = sum(o.total_amount for o in orders) or Decimal(0)
    # 有效订单（不含取消/退款）用于计算平均客单价
    valid_statuses = ("pending", "paid", "shipped", "completed")
    valid_orders = [
        o
        for o in orders
        if (o.status.value if hasattr(o.status, "value") else o.status)
        in valid_statuses
    ]
    valid_amount = sum(o.total_amount for o in valid_orders) or Decimal(0)
    avg_order = valid_amount / len(valid_orders) if valid_orders else Decimal(0)

    return success_response(
        {
            "period": {"start": start.isoformat(), "end": end.isoformat()},
            "total_orders": total_orders,
            "pending_count": by_status["pending"][0],
            "pending_amount": float(by_status["pending"][1]),
            "paid_count": by_status["paid"][0],
            "paid_amount": float(by_status["paid"][1]),
            "shipped_count": by_status["shipped"][0],
            "shipped_amount": float(by_status["shipped"][1]),
            "completed_count": by_status["completed"][0],
            "completed_amount": float(by_status["completed"][1]),
            "cancelled_count": by_status["cancelled"][0],
            "cancelled_amount": float(by_status["cancelled"][1]),
            "refunded_count": by_status["refunded"][0],
            "refunded_amount": float(by_status["refunded"][1]),
            "total_amount": float(total_amount),
            "avg_order_value": float(avg_order),
        }
    )


# 订单状态分布
@router.get("/by-status", response_model=dict, dependencies=[Depends(check_module_permission("order_analysis"))])
async def orders_by_status(
    date_range: str = Query("today"),
    start_date: str = Query(None),
    end_date: str = Query(None),
    db: Session = Depends(get_db),
):
    start, end = parse_date_range(date_range, start_date, end_date)

    orders = (
        db.query(Order)
        .filter(
            Order.created_at >= datetime.combine(start, datetime.min.time()),
            Order.created_at <= datetime.combine(end, datetime.max.time()),
        )
        .all()
    )

    status_dist = {}
    for order in orders:
        status = order.status
        if status not in status_dist:
            status_dist[status] = {"count": 0, "amount": Decimal(0)}
        status_dist[status]["count"] += 1
        status_dist[status]["amount"] += order.total_amount

    data = [
        {
            "status": status,
            "count": stats["count"],
            "amount": float(stats["amount"]),
            "percentage": (
                round((stats["count"] / len(orders) * 100), 2) if orders else 0
            ),
        }
        for status, stats in status_dist.items()
    ]

    return success_response(
        {"period": {"start": start.isoformat(), "end": end.isoformat()}, "data": data}
    )


# 订单转化漏斗（下单 → 付款 → 发货 → 完成）
@router.get("/funnel", response_model=dict, dependencies=[Depends(check_module_permission("order_analysis"))])
async def order_funnel(
    date_range: str = Query("today"),
    start_date: str = Query(None),
    end_date: str = Query(None),
    db: Session = Depends(get_db),
):
    start, end = parse_date_range(date_range, start_date, end_date)

    all_orders = (
        db.query(Order)
        .filter(
            Order.created_at >= datetime.combine(start, datetime.min.time()),
            Order.created_at <= datetime.combine(end, datetime.max.time()),
        )
        .all()
    )

    total = len(all_orders)
    pending = len([o for o in all_orders if o.status == "pending"])
    paid = len([o for o in all_orders if o.status in ["paid", "shipped", "completed"]])
    shipped = len([o for o in all_orders if o.status in ["shipped", "completed"]])
    completed = len([o for o in all_orders if o.status == "completed"])

    funnel_data = [
        {"stage": "All Orders", "count": total, "percentage": 100},
        {
            "stage": "Paid",
            "count": paid,
            "percentage": round((paid / total * 100), 2) if total > 0 else 0,
        },
        {
            "stage": "Shipped",
            "count": shipped,
            "percentage": round((shipped / total * 100), 2) if total > 0 else 0,
        },
        {
            "stage": "Completed",
            "count": completed,
            "percentage": round((completed / total * 100), 2) if total > 0 else 0,
        },
    ]

    return success_response(
        {
            "period": {"start": start.isoformat(), "end": end.isoformat()},
            "data": funnel_data,
        }
    )


# 退款分析：退款金额、退款率、退款原因分布
@router.get("/refund-analysis", response_model=dict, dependencies=[Depends(check_module_permission("order_analysis"))])
async def refund_analysis(
    date_range: str = Query("last_30_days"),
    start_date: str = Query(None),
    end_date: str = Query(None),
    db: Session = Depends(get_db),
):
    start, end = parse_date_range(date_range, start_date, end_date)

    refunds = (
        db.query(Refund)
        .filter(
            Refund.created_at >= datetime.combine(start, datetime.min.time()),
            Refund.created_at <= datetime.combine(end, datetime.max.time()),
        )
        .all()
    )

    total_refund_amount = sum(r.refund_amount for r in refunds) or Decimal(0)
    completed_refunds = [r for r in refunds if r.status == "completed"]
    completed_amount = sum(r.refund_amount for r in completed_refunds) or Decimal(0)

    reason_stats = {}
    for refund in refunds:
        reason = refund.reason
        if reason not in reason_stats:
            reason_stats[reason] = {"count": 0, "amount": Decimal(0)}
        reason_stats[reason]["count"] += 1
        reason_stats[reason]["amount"] += refund.refund_amount

    total_orders = (
        db.query(Order)
        .filter(
            Order.created_at >= datetime.combine(start, datetime.min.time()),
            Order.created_at <= datetime.combine(end, datetime.max.time()),
        )
        .count()
    )

    return success_response(
        {
            "period": {"start": start.isoformat(), "end": end.isoformat()},
            "total_refunds": len(refunds),
            "completed_refunds": len(completed_refunds),
            "total_refund_amount": float(total_refund_amount),
            "completed_refund_amount": float(completed_amount),
            "refund_rate": (
                round((len(refunds) / total_orders * 100), 2) if total_orders > 0 else 0
            ),
            "by_reason": [
                {
                    "reason": reason,
                    "count": stats["count"],
                    "amount": float(stats["amount"]),
                }
                for reason, stats in sorted(
                    reason_stats.items(), key=lambda x: x[1]["count"], reverse=True
                )
            ],
        }
    )


# 订单时间线：按天统计订单数和总金额，缺失日期补零
@router.get("/timeline", response_model=dict, dependencies=[Depends(check_module_permission("order_analysis"))])
async def order_timeline(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    today = date.today()
    start = today - timedelta(days=days - 1)
    s_dt = datetime.combine(start, datetime.min.time())
    e_dt = datetime.combine(today, datetime.max.time())

    day_col = func.date(Order.created_at).label("d")
    rows = (
        db.query(
            day_col,
            func.count(Order.id).label("cnt"),
            func.coalesce(func.sum(Order.total_amount), 0).label("amt"),
        )
        .filter(Order.created_at >= s_dt, Order.created_at <= e_dt)
        .group_by(day_col)
        .all()
    )
    by_day = {str(r.d): (int(r.cnt), Decimal(str(r.amt))) for r in rows}

    timeline_data = []
    for i in range(days):
        day = start + timedelta(days=i)
        cnt, amt = by_day.get(day.isoformat(), (0, Decimal(0)))
        timeline_data.append(
            {
                "date": day.isoformat(),
                "order_count": cnt,
                "total_amount": float(amt),
                "avg_order_value": float(amt / cnt) if cnt else 0,
            }
        )

    return success_response({"period_days": days, "data": timeline_data})


# 订单列表（分页 + 状态/日期筛选）
@router.get("/list", response_model=dict, dependencies=[Depends(check_module_permission("order_analysis"))])
async def orders_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=10000),
    status_filter: str = Query(None, alias="status"),
    date_filter: str = Query(None, alias="date"),
    db: Session = Depends(get_db),
):
    query = db.query(Order)
    if status_filter:
        query = query.filter(Order.status == status_filter)
    if date_filter:
        try:
            target = date.fromisoformat(date_filter)
            s_dt = datetime.combine(target, datetime.min.time())
            e_dt = datetime.combine(target, datetime.max.time())
            query = query.filter(Order.created_at >= s_dt, Order.created_at <= e_dt)
        except ValueError:
            pass

    total = query.count()
    orders = (
        query.order_by(Order.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    data = []
    for order in orders:
        customer = order.customer
        data.append(
            {
                "order_id": order.id,
                "order_no": order.order_no,
                "customer": customer.username if customer else "Unknown",
                "total_amount": float(order.total_amount),
                "status": (
                    order.status.value
                    if hasattr(order.status, "value")
                    else order.status
                ),
                "created_at": (
                    order.created_at.isoformat() if order.created_at else None
                ),
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


# 大额订单查询（金额超过指定阈值）
@router.get("/large-orders", response_model=dict, dependencies=[Depends(check_module_permission("order_analysis"))])
async def large_orders(
    min_amount: float = Query(1000),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    orders = (
        db.query(Order)
        .filter(Order.total_amount >= Decimal(str(min_amount)))
        .order_by(Order.total_amount.desc())
        .limit(limit)
        .all()
    )

    data = []
    for order in orders:
        customer = order.customer
        data.append(
            {
                "order_id": order.id,
                "order_no": order.order_no,
                "customer": customer.username if customer else "Unknown",
                "total_amount": float(order.total_amount),
                "status": order.status,
                "created_at": (
                    order.created_at.isoformat() if order.created_at else None
                ),
            }
        )

    return success_response(
        {"min_amount": min_amount, "count": len(data), "data": data}
    )
