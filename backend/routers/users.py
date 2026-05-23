from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Optional
from database import get_db
from dependencies import check_module_permission
from models import Customer, Order
from utils import success_response, new_customer_threshold, customer_type_label

router = APIRouter()


# 客户列表（分页 + 筛选，新老客按注册时间实时判定）
@router.get("/customers/list", response_model=dict, dependencies=[Depends(check_module_permission("user_analysis"))])
def customers_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=10000),
    gender: Optional[str] = Query(None),
    age_group: Optional[str] = Query(None),
    province: Optional[str] = Query(None),
    customer_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Customer)
    if gender:
        q = q.filter(Customer.gender == gender)
    if age_group:
        q = q.filter(Customer.age_group == age_group)
    if province:
        q = q.filter(Customer.province == province)
    # 用注册时间窗口判定新老客，不读 DB 中 customer_type 字段
    if customer_type == "new":
        q = q.filter(Customer.registered_at >= new_customer_threshold())
    elif customer_type == "returning":
        q = q.filter(Customer.registered_at < new_customer_threshold())
    total = q.count()
    rows = (
        q.order_by(Customer.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return success_response(
        {
            "data": [
                {
                    "id": c.id,
                    "username": c.username,
                    "gender": c.gender.value if c.gender else None,
                    "age_group": c.age_group.value if c.age_group else None,
                    "province": c.province,
                    "customer_type": customer_type_label(c.registered_at),
                    "registered_at": (
                        c.registered_at.isoformat() if c.registered_at else None
                    ),
                }
                for c in rows
            ],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size,
            },
        }
    )


# 用户概览统计：总数、新客、老客、复购客、今日活跃
@router.get("/overview", response_model=dict, dependencies=[Depends(check_module_permission("user_analysis"))])
async def users_overview(db: Session = Depends(get_db)):
    total_customers = db.query(Customer).count()
    threshold = new_customer_threshold()
    new_customers = (
        db.query(Customer).filter(Customer.registered_at >= threshold).count()
    )
    returning_customers = (
        db.query(Customer).filter(Customer.registered_at < threshold).count()
    )

    # 拥有 2 笔及以上订单的客户数
    repeat_customers = (
        db.query(Order.customer_id)
        .filter(Order.customer_id.isnot(None))
        .group_by(Order.customer_id)
        .having(func.count(Order.id) >= 2)
        .count()
    )

    today = date.today()
    active_today = (
        db.query(Customer)
        .join(Order, Customer.id == Order.customer_id)
        .filter(
            Order.created_at >= datetime.combine(today, datetime.min.time()),
            Order.created_at <= datetime.combine(today, datetime.max.time()),
        )
        .distinct()
        .count()
    )

    return success_response(
        {
            "total_customers": total_customers,
            "new_customers": new_customers,
            "returning_customers": returning_customers,
            "repeat_customers": repeat_customers,
            "active_today": active_today,
        }
    )


# 按年龄段分布统计
@router.get("/by-age-group", response_model=dict, dependencies=[Depends(check_module_permission("user_analysis"))])
async def users_by_age_group(db: Session = Depends(get_db)):
    customers = db.query(Customer).all()

    age_group_stats = {}
    for customer in customers:
        ag = customer.age_group.value if customer.age_group else "Unknown"
        if ag not in age_group_stats:
            age_group_stats[ag] = 0
        age_group_stats[ag] += 1

    data = [
        {
            "age_group": ag,
            "count": count,
            "percentage": round((count / len(customers) * 100), 2) if customers else 0,
        }
        for ag, count in sorted(age_group_stats.items())
    ]

    return success_response(data)


# 按省份分布统计
@router.get("/by-province", response_model=dict, dependencies=[Depends(check_module_permission("user_analysis"))])
async def users_by_province(
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
):
    customers = db.query(Customer).all()

    province_stats = {}
    for customer in customers:
        prov = customer.province or "Unknown"
        if prov not in province_stats:
            province_stats[prov] = 0
        province_stats[prov] += 1

    data = [
        {"province": prov, "count": count}
        for prov, count in sorted(
            province_stats.items(), key=lambda x: x[1], reverse=True
        )[:limit]
    ]

    return success_response({"total_provinces": len(province_stats), "data": data})


# 按性别分布统计
@router.get("/by-gender", response_model=dict, dependencies=[Depends(check_module_permission("user_analysis"))])
async def users_by_gender(db: Session = Depends(get_db)):
    customers = db.query(Customer).all()

    gender_stats = {}
    for customer in customers:
        gen = customer.gender.value if customer.gender else "Unknown"
        if gen not in gender_stats:
            gender_stats[gen] = 0
        gender_stats[gen] += 1

    data = [
        {
            "gender": gen,
            "count": count,
            "percentage": round((count / len(customers) * 100), 2) if customers else 0,
        }
        for gen, count in sorted(gender_stats.items())
    ]

    return success_response(data)


# 用户注册增长趋势（按天统计）
@router.get("/growth", response_model=dict, dependencies=[Depends(check_module_permission("user_analysis"))])
async def user_growth(
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
):
    today = date.today()
    start = today - timedelta(days=days - 1)

    growth_data = []
    cumulative = 0

    for i in range(days):
        day = start + timedelta(days=i)
        daily_new = (
            db.query(Customer)
            .filter(
                Customer.registered_at >= datetime.combine(day, datetime.min.time()),
                Customer.registered_at <= datetime.combine(day, datetime.max.time()),
            )
            .count()
        )

        cumulative += daily_new
        growth_data.append(
            {"date": day.isoformat(), "new_users": daily_new, "cumulative": cumulative}
        )

    return success_response({"period_days": days, "data": growth_data})


# RFM 分析（最近购买、购买频次、消费金额）
@router.get("/rfm-analysis", response_model=dict, dependencies=[Depends(check_module_permission("user_analysis"))])
async def rfm_analysis(db: Session = Depends(get_db)):
    today = datetime.utcnow()
    reference_date = today.date()

    customers = db.query(Customer).all()
    rfm_data = []

    for customer in customers:
        orders = (
            db.query(Order)
            .filter(
                Order.customer_id == customer.id,
                Order.status.in_(["paid", "shipped", "completed"]),
            )
            .all()
        )

        if not orders:
            continue

        last_order = max(orders, key=lambda x: x.created_at)
        recency = (reference_date - last_order.created_at.date()).days
        frequency = len(orders)
        monetary = sum(o.total_amount for o in orders) or Decimal(0)

        rfm_data.append(
            {
                "customer_id": customer.id,
                "username": customer.username,
                "recency_days": recency,
                "frequency": frequency,
                "monetary_value": float(monetary),
                "avg_order_value": float(monetary / frequency) if frequency > 0 else 0,
            }
        )

    rfm_data.sort(key=lambda x: x["monetary_value"], reverse=True)

    return success_response(
        {
            "total_active_customers": len(rfm_data),
            "data": rfm_data[:100],
        }
    )


# 按注册月份的用户队列分析
@router.get("/cohort", response_model=dict, dependencies=[Depends(check_module_permission("user_analysis"))])
async def cohort_analysis(db: Session = Depends(get_db)):
    customers = db.query(Customer).all()

    cohort_data = {}
    for customer in customers:
        if not customer.registered_at:
            continue

        cohort_month = customer.registered_at.strftime("%Y-%m")
        if cohort_month not in cohort_data:
            cohort_data[cohort_month] = {"registered": 0, "active_today": 0}
        cohort_data[cohort_month]["registered"] += 1

        today = date.today()
        orders = (
            db.query(Order)
            .filter(
                Order.customer_id == customer.id,
                Order.created_at >= datetime(today.year, today.month, 1),
                Order.created_at
                < datetime(
                    today.year,
                    today.month if today.month < 12 else 1,
                    1 if today.month < 12 else 1 + 12,
                ),
            )
            .count()
        )

        if orders > 0:
            cohort_data[cohort_month]["active_today"] += 1

    data = [
        {
            "cohort_month": month,
            "registered_users": stats["registered"],
            "active_users": stats["active_today"],
            "retention_rate": (
                round((stats["active_today"] / stats["registered"] * 100), 2)
                if stats["registered"] > 0
                else 0
            ),
        }
        for month, stats in sorted(cohort_data.items())
    ]

    return success_response({"total_cohorts": len(data), "data": data})
