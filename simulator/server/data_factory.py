"""CRUD + 级联逻辑。所有写入操作的真理之源。

约定:
- list_*  函数返回 {"data": [...], "pagination": {...}}
- create_*/update_*/delete_* 函数返回单行 dict,失败时返回 None 或字符串错误码
- 级联的 stock_alert / refund_alert / finance 同步由这里完成

冲突错误码:
- "has_orders" — 删客户但客户存在订单
- "in_use"     — 删商品但商品出现在 order_items
"""
import random
import threading
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List, Union
from sqlalchemy import func
from sqlalchemy.orm import Session


# ─── 时钟覆盖(回填模式)─────────────────────────────────────────────────
# 自动化引擎可以在 tick 前往 _clock.override 写入一个 datetime,该 worker 线程
# 内所有走 _now() 的写入(订单、客户、财务流水、推进时间戳等)都会用这个时间,
# 实现"把生成数据回填到指定历史日期"。tick 结束后清空,不污染其他请求。
_clock = threading.local()


def _now() -> datetime:
    return getattr(_clock, "override", None) or datetime.utcnow()


def set_clock_override(ts: Optional[datetime]) -> None:
    _clock.override = ts


from models import (
    Customer, Product, Order, OrderItem, FinanceRecord, Notification, Refund,
    CategoryEnum, GenderEnum, AgeGroupEnum, CustomerTypeEnum,
    OrderStatusEnum, ProductStatusEnum,
    FinanceTypeEnum, FinanceCategoryEnum,
    NotificationTypeEnum, RefundStatusEnum, RefundReasonEnum,
)


# ─── 通知触发阈值 ──────────────────────────────────────────────────────
REFUND_ALERT_THRESHOLD     = Decimal("3000")   # 退款金额 ≥ 此值触发 refund_alert
LARGE_ORDER_THRESHOLD      = Decimal("3000")  # 单笔订单金额 ≥ 此值触发 order_alert
RAPID_ORDER_WINDOW_MIN     = 10                 # 高频检测窗口(分钟)
RAPID_ORDER_COUNT          = 3                 # 窗口内订单数 ≥ 此值触发 order_alert
RAPID_ORDER_DEBOUNCE_MIN   = 60                # 同客户已触发后多少分钟内不重发
SALES_DEVIATION_RATIO      = Decimal("0.3")    # 当日累计 vs 7 日均偏离 ≥ 此比例触发 sales_alert
SALES_BASELINE_DAYS        = 5                 # 用过去 N 天日均做基线
SALES_ALERT_CHECK_HOUR     = 23                # 仅当 _now().hour ≥ 此值时才扫销售额波动(每日临近收盘)


# ─── 订单状态机:单向不可逆,有终态 ─────────────────────────────────────
# pending → {paid, cancelled}
# paid    → {shipped, refunded}
# shipped → {completed}
# completed / cancelled / refunded → 终态(不可转出)
ALLOWED_ORDER_TRANSITIONS: Dict[OrderStatusEnum, set] = {
    OrderStatusEnum.pending:   {OrderStatusEnum.paid, OrderStatusEnum.cancelled},
    OrderStatusEnum.paid:      {OrderStatusEnum.shipped, OrderStatusEnum.refunded},
    OrderStatusEnum.shipped:   {OrderStatusEnum.completed},
    OrderStatusEnum.completed: set(),
    OrderStatusEnum.cancelled: set(),
    OrderStatusEnum.refunded:  set(),
}


PROVINCES = [
    # 直辖市
    "北京", "上海", "天津", "重庆",
    # 省
    "河北", "山西", "辽宁", "吉林", "黑龙江",
    "江苏", "浙江", "安徽", "福建", "江西",
    "山东", "河南", "湖北", "湖南", "广东",
    "海南", "四川", "贵州", "云南", "陕西",
    "甘肃", "青海", "台湾",
    # 自治区
    "内蒙古", "广西", "西藏", "宁夏", "新疆",
    # 特别行政区
    "香港", "澳门",
]


def _enum_or_random(enum_cls, value):
    if value:
        try:
            return enum_cls(value)
        except ValueError:
            pass
    return random.choice(list(enum_cls))


def _enum_value(v):
    return v.value if hasattr(v, "value") else v


def _paginate(query, page: int, page_size: int) -> Dict[str, Any]:
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "rows": rows,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size if total else 0,
        },
    }


# ─── Serializers ────────────────────────────────────────────────────────

def _ser_customer(c: Customer) -> Dict[str, Any]:
    return {
        "id": c.id,
        "username": c.username,
        "gender": _enum_value(c.gender),
        "age_group": _enum_value(c.age_group),
        "province": c.province,
        "customer_type": _enum_value(c.customer_type),
        "registered_at": c.registered_at.isoformat() if c.registered_at else None,
    }


def _ser_product(p: Product) -> Dict[str, Any]:
    return {
        "id": p.id,
        "product_name": p.product_name,
        "category": _enum_value(p.category),
        "price": float(p.price),
        "cost": float(p.cost),
        "stock": p.stock,
        "low_stock_threshold": p.low_stock_threshold,
        "status": _enum_value(p.status),
    }


def _ser_order(o: Order) -> Dict[str, Any]:
    return {
        "id": o.id,
        "order_no": o.order_no,
        "customer_id": o.customer_id,
        "customer": o.customer.username if o.customer else None,
        "total_amount": float(o.total_amount),
        "status": _enum_value(o.status),
        "created_at": o.created_at.isoformat() if o.created_at else None,
        "paid_at": o.paid_at.isoformat() if o.paid_at else None,
        "completed_at": o.completed_at.isoformat() if o.completed_at else None,
    }


def _ser_refund(r: Refund) -> Dict[str, Any]:
    return {
        "id": r.id,
        "order_id": r.order_id,
        "refund_amount": float(r.refund_amount),
        "reason": _enum_value(r.reason),
        "status": _enum_value(r.status),
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def _ser_finance(f: FinanceRecord) -> Dict[str, Any]:
    return {
        "id": f.id,
        "type": _enum_value(f.type),
        "category": _enum_value(f.category),
        "amount": float(f.amount),
        "related_order_id": f.related_order_id,
        "recorded_at": f.recorded_at.isoformat() if f.recorded_at else None,
    }


def _ser_notification(n: Notification) -> Dict[str, Any]:
    return {
        "id": n.id,
        "type": _enum_value(n.type),
        "title": n.title,
        "content": n.content,
        "is_read": bool(n.is_read),
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


# ─── Counts ─────────────────────────────────────────────────────────────

def get_counts(db: Session) -> Dict[str, int]:
    return {
        "customers":       db.query(Customer).count(),
        "products":        db.query(Product).count(),
        "orders":          db.query(Order).count(),
        "refunds":         db.query(Refund).count(),
        "finance_records": db.query(FinanceRecord).count(),
        "notifications":   db.query(Notification).count(),
    }


# ─── List ───────────────────────────────────────────────────────────────

def list_customers(db, page=1, page_size=20, *, gender=None, age_group=None, province=None, customer_type=None):
    q = db.query(Customer)
    if gender:        q = q.filter(Customer.gender == gender)
    if age_group:     q = q.filter(Customer.age_group == age_group)
    if province:      q = q.filter(Customer.province == province)
    if customer_type: q = q.filter(Customer.customer_type == customer_type)
    q = q.order_by(Customer.id.desc())
    result = _paginate(q, page, page_size)
    return {"data": [_ser_customer(c) for c in result["rows"]], "pagination": result["pagination"]}


def list_products(db, page=1, page_size=20, *, category=None, status=None):
    q = db.query(Product)
    if category: q = q.filter(Product.category == category)
    if status:   q = q.filter(Product.status == status)
    q = q.order_by(Product.id.desc())
    result = _paginate(q, page, page_size)
    return {"data": [_ser_product(p) for p in result["rows"]], "pagination": result["pagination"]}


def list_orders(db, page=1, page_size=20, *, status=None):
    q = db.query(Order)
    if status: q = q.filter(Order.status == status)
    q = q.order_by(Order.id.desc())
    result = _paginate(q, page, page_size)
    return {"data": [_ser_order(o) for o in result["rows"]], "pagination": result["pagination"]}


def list_refunds(db, page=1, page_size=20, *, status=None):
    q = db.query(Refund)
    if status: q = q.filter(Refund.status == status)
    q = q.order_by(Refund.id.desc())
    result = _paginate(q, page, page_size)
    return {"data": [_ser_refund(r) for r in result["rows"]], "pagination": result["pagination"]}


def list_finance_records(db, page=1, page_size=20, *, type_=None, category=None):
    q = db.query(FinanceRecord)
    if type_:    q = q.filter(FinanceRecord.type == type_)
    if category: q = q.filter(FinanceRecord.category == category)
    q = q.order_by(FinanceRecord.id.desc())
    result = _paginate(q, page, page_size)
    return {"data": [_ser_finance(f) for f in result["rows"]], "pagination": result["pagination"]}


def list_notifications(db, page=1, page_size=20, *, ntype=None, is_read=None):
    q = db.query(Notification)
    if ntype:           q = q.filter(Notification.type == ntype)
    if is_read is not None: q = q.filter(Notification.is_read == is_read)
    q = q.order_by(Notification.id.desc())
    result = _paginate(q, page, page_size)
    return {"data": [_ser_notification(n) for n in result["rows"]], "pagination": result["pagination"]}


# ─── 级联辅助 ───────────────────────────────────────────────────────────

def _push_stock_alert(db: Session, product: Product) -> Optional[Dict[str, Any]]:
    """库存跌破阈值时,落一条 stock_alert 通知。返回通知 dict 或 None。"""
    if product.stock < product.low_stock_threshold:
        n = Notification(
            type=NotificationTypeEnum.stock_alert,
            title="库存预警",
            content=f"商品《{product.product_name}》库存仅剩 {product.stock} 件,低于阈值 {product.low_stock_threshold} 件",
            is_read=False,
            created_at=_now(),
        )
        db.add(n)
        db.flush()
        return _ser_notification(n)
    return None


def _clear_stock_alerts(db: Session, product_name: str) -> List[int]:
    """商品库存恢复到阈值以上时,删除该商品现存的所有 stock_alert 通知。

    用 content LIKE '商品《X》%' 定位(_push_stock_alert 写入的格式),返回被删除的通知 ID。
    """
    rows = (
        db.query(Notification)
        .filter(
            Notification.type == NotificationTypeEnum.stock_alert,
            Notification.content.like(f"商品《{product_name}》%"),
        )
        .all()
    )
    ids = [n.id for n in rows]
    for n in rows:
        db.delete(n)
    db.flush()
    return ids


def sweep_stale_stock_alerts(db: Session) -> List[int]:
    """扫描所有 stock_alert 通知,反查对应商品,凡当前 stock >= threshold 的,删除该通知。

    用于 simulator 启动时 / 用户手动调用,清理"商品库存已恢复但预警通知还遗留"的历史记录。
    返回被删除的通知 ID 列表。
    """
    import re
    alerts = (
        db.query(Notification)
        .filter(Notification.type == NotificationTypeEnum.stock_alert)
        .all()
    )
    if not alerts:
        return []
    name_re = re.compile(r"^商品《(.+?)》")
    products = {p.product_name: p for p in db.query(Product).all()}
    deleted: List[int] = []
    for n in alerts:
        m = name_re.match(n.content or "")
        if not m:
            continue
        p = products.get(m.group(1))
        if p is not None and p.stock >= p.low_stock_threshold:
            deleted.append(n.id)
            db.delete(n)
    if deleted:
        db.commit()
    return deleted


def _order_product_cost(db: Session, order_id: int) -> Decimal:
    """计算订单的商品成本:SUM(qty × product.cost)。单条 JOIN+SUM,替代 N+1 查询。"""
    result = (
        db.query(func.coalesce(func.sum(OrderItem.quantity * Product.cost), 0))
        .join(Product, Product.id == OrderItem.product_id)
        .filter(OrderItem.order_id == order_id)
        .scalar()
    )
    return Decimal(str(result or 0)).quantize(Decimal("0.01"))


def _add_sale_finance(db: Session, order: Order) -> List[Dict[str, Any]]:
    """订单进入 paid 时,补 3 条 finance(sales_income + product_cost + ad_cost)。

    幂等:若 order 已经有这些 category 的记录,会先跳过(由调用方保证只在
    pending→paid 边界调用一次,这里不做额外校验)。
    """
    now = _now()
    subtotal = order.total_amount or Decimal("0")
    product_cost = _order_product_cost(db, order.id)
    records = [
        FinanceRecord(
            type=FinanceTypeEnum.income, category=FinanceCategoryEnum.sales_income,
            amount=subtotal, related_order_id=order.id, recorded_at=now,
        ),
        FinanceRecord(
            type=FinanceTypeEnum.expense, category=FinanceCategoryEnum.product_cost,
            amount=product_cost, related_order_id=order.id, recorded_at=now,
        ),
        FinanceRecord(
            type=FinanceTypeEnum.expense, category=FinanceCategoryEnum.ad_cost,
            amount=(subtotal * Decimal("0.05")).quantize(Decimal("0.01")),
            related_order_id=order.id, recorded_at=now,
        ),
    ]
    db.add_all(records)
    db.flush()
    return [_ser_finance(r) for r in records]


def _add_logistics_finance(db: Session, order: Order) -> List[Dict[str, Any]]:
    """订单进入 shipped 时,补 1 条 logistics_cost。"""
    now = _now()
    subtotal = order.total_amount or Decimal("0")
    record = FinanceRecord(
        type=FinanceTypeEnum.expense, category=FinanceCategoryEnum.logistics_cost,
        amount=(subtotal * Decimal("0.08")).quantize(Decimal("0.01")),
        related_order_id=order.id, recorded_at=now,
    )
    db.add(record)
    db.flush()
    return [_ser_finance(record)]


def _add_refund_finance(db: Session, order: Order) -> List[Dict[str, Any]]:
    """订单从 paid 转 refunded 时,补 1 条 refund_out 支出。

    注意:不删除该订单已有的 sales_income / product_cost / ad_cost,
    收入和成本仍记账,退款作为单独的支出条目体现资金流出。
    """
    now = _now()
    record = FinanceRecord(
        type=FinanceTypeEnum.expense, category=FinanceCategoryEnum.refund_out,
        amount=order.total_amount or Decimal("0"),
        related_order_id=order.id, recorded_at=now,
    )
    db.add(record)
    db.flush()
    return [_ser_finance(record)]


def _remove_finance_for_order(db: Session, order_id: int) -> int:
    """删订单相关的所有 finance_records。返回删除条数。"""
    return db.query(FinanceRecord).filter(FinanceRecord.related_order_id == order_id).delete()


# ─── 业务预警通知 helper(refund / order / sales)─────────────────────

def _push_refund_alert(db: Session, order: Order, amount: Decimal) -> Optional[Dict[str, Any]]:
    """退款金额 ≥ REFUND_ALERT_THRESHOLD 时写 refund_alert 通知。
    任何"资金流出退还客户"的路径都调它(create_refund / 状态机 paid→refunded)。
    """
    if amount < REFUND_ALERT_THRESHOLD:
        return None
    n = Notification(
        type=NotificationTypeEnum.refund_alert,
        title="大额退款",
        content=f"订单 {order.order_no} 发生退款,金额 ¥{float(amount):.2f}",
        is_read=False,
        created_at=_now(),
    )
    db.add(n)
    db.flush()
    return _ser_notification(n)


def _push_order_alert(db: Session, order: Order, customer: Customer) -> Optional[Dict[str, Any]]:
    """异常订单检测。

    规则 A: 单笔金额 ≥ LARGE_ORDER_THRESHOLD
    规则 B: 同客户在 RAPID_ORDER_WINDOW_MIN 内已下 ≥ RAPID_ORDER_COUNT 单 —— 开发期间停用
    """
    title = "异常订单"
    content: Optional[str] = None

    # 规则 A:单笔超大金额
    if (order.total_amount or Decimal("0")) >= LARGE_ORDER_THRESHOLD:
        content = (
            f"订单 {order.order_no} 金额 ¥{float(order.total_amount):.2f},"
            f"超过大额阈值 ¥{float(LARGE_ORDER_THRESHOLD):.0f}"
        )

    # ── 规则 B(开发期间停用):同客户高频下单 ──────────────────────────
    # if not content:
    #     window_start = _now() - timedelta(minutes=RAPID_ORDER_WINDOW_MIN)
    #     cnt = (
    #         db.query(Order)
    #         .filter(Order.customer_id == customer.id, Order.created_at >= window_start)
    #         .count()
    #     )
    #     if cnt >= RAPID_ORDER_COUNT:
    #         content = (
    #             f"客户 {customer.username} 在 {RAPID_ORDER_WINDOW_MIN}min 内下了 {cnt} 单,疑似刷单"
    #         )
    #         # 规则 B 防抖:同客户在过去 RAPID_ORDER_DEBOUNCE_MIN 分钟内已有相关 order_alert 就跳过
    #         debounce_start = _now() - timedelta(minutes=RAPID_ORDER_DEBOUNCE_MIN)
    #         recent = (
    #             db.query(Notification)
    #             .filter(
    #                 Notification.type == NotificationTypeEnum.order_alert,
    #                 Notification.content.like(f"%客户 {customer.username}%"),
    #                 Notification.created_at >= debounce_start,
    #             )
    #             .first()
    #         )
    #         if recent:
    #             content = None

    if not content:
        return None

    n = Notification(
        type=NotificationTypeEnum.order_alert,
        title=title,
        content=content,
        is_read=False,
        created_at=_now(),
    )
    db.add(n)
    db.flush()
    return _ser_notification(n)


def _push_sales_alert(db: Session) -> Optional[Dict[str, Any]]:
    """销售额波动检测:今日累计 vs 近 SALES_BASELINE_DAYS 天日均。

    门控:只在每日 SALES_ALERT_CHECK_HOUR(默认 23 点)及以后的 tick 才扫,
    避免日间订单频繁触发 + 回填模式下每个历史日期被多次刷屏。
    再叠加"同日同方向 24h 内只发 1 条"的 content marker 去重。
    """
    now = _now()
    if now.hour < SALES_ALERT_CHECK_HOUR:
        return None

    today = now.date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end   = datetime.combine(today, datetime.max.time())
    base_start  = datetime.combine(today - timedelta(days=SALES_BASELINE_DAYS), datetime.min.time())
    base_end    = datetime.combine(today - timedelta(days=1), datetime.max.time())

    paid_statuses = ["paid", "shipped", "completed"]

    today_sum = (
        db.query(func.coalesce(func.sum(Order.total_amount), 0))
        .filter(
            Order.created_at >= today_start,
            Order.created_at <= today_end,
            Order.status.in_(paid_statuses),
        )
        .scalar()
    ) or 0
    base_sum = (
        db.query(func.coalesce(func.sum(Order.total_amount), 0))
        .filter(
            Order.created_at >= base_start,
            Order.created_at <= base_end,
            Order.status.in_(paid_statuses),
        )
        .scalar()
    ) or 0

    base_avg = Decimal(str(base_sum)) / Decimal(SALES_BASELINE_DAYS)
    if base_avg <= 0:
        return None  # 无基线数据,不报警

    today_amt = Decimal(str(today_sum))
    ratio = (today_amt - base_avg) / base_avg
    if ratio <= -SALES_DEVIATION_RATIO:
        direction = "偏低"
    elif ratio >= SALES_DEVIATION_RATIO:
        direction = "偏高"
    else:
        return None

    # 防抖:今日同方向已发过就跳过(content 含 "YYYY-MM-DD·偏X" marker)
    marker = f"{today.isoformat()}·{direction}"
    if db.query(Notification).filter(
        Notification.type == NotificationTypeEnum.sales_alert,
        Notification.content.like(f"%{marker}%"),
        Notification.created_at >= today_start,
    ).first():
        return None

    n = Notification(
        type=NotificationTypeEnum.sales_alert,
        title="销售额波动",
        content=(
            f"{marker}: 今日累计 ¥{float(today_amt):.0f},"
            f"较近 {SALES_BASELINE_DAYS} 日日均 ¥{float(base_avg):.0f} {direction} "
            f"{abs(float(ratio) * 100):.0f}%"
        ),
        is_read=False,
        created_at=_now(),
    )
    db.add(n)
    db.flush()
    return _ser_notification(n)


# ─── Customer ──────────────────────────────────────────────────────────

def create_customer(db, *, gender=None, age_group=None, province=None, customer_type=None) -> Dict[str, Any]:
    """新规则:任何新注册客户初始一律为 'new',backend 查询时按 registered_at 实时判定。
    customer_type 入参保留向后兼容(simulator UI 仍可指定),但默认 new。
    """
    last_id = db.query(Customer.id).order_by(Customer.id.desc()).first()
    next_seq = (last_id[0] if last_id else 0) + 1
    c = Customer(
        username=f"customer{next_seq:05d}",
        gender=_enum_or_random(GenderEnum, gender),
        age_group=_enum_or_random(AgeGroupEnum, age_group),
        province=province if province in PROVINCES else random.choice(PROVINCES),
        # 注册即新客;backend 按 registered_at 重新算
        customer_type=CustomerTypeEnum(customer_type) if customer_type else CustomerTypeEnum.new,
        registered_at=_now(),
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return _ser_customer(c)


def update_customer(db, id, **fields) -> Optional[Dict[str, Any]]:
    c = db.query(Customer).filter(Customer.id == id).first()
    if not c:
        return None
    if "username" in fields and fields["username"]:
        c.username = fields["username"]
    if fields.get("gender"):        c.gender = GenderEnum(fields["gender"])
    if fields.get("age_group"):     c.age_group = AgeGroupEnum(fields["age_group"])
    if fields.get("province"):      c.province = fields["province"]
    if fields.get("customer_type"): c.customer_type = CustomerTypeEnum(fields["customer_type"])
    db.commit()
    db.refresh(c)
    return _ser_customer(c)


def delete_customer(db, id) -> Union[Dict[str, Any], str, None]:
    c = db.query(Customer).filter(Customer.id == id).first()
    if not c:
        return None
    if db.query(Order).filter(Order.customer_id == id).count() > 0:
        return "has_orders"
    info = _ser_customer(c)
    db.delete(c)
    db.commit()
    return info


def delete_customers(db, ids: List[int]) -> Dict[str, Any]:
    """批量删除客户。有订单关联的跳过,返回成功/跳过两组。"""
    deleted: List[int] = []
    skipped: List[Dict[str, Any]] = []
    for cid in ids:
        c = db.query(Customer).filter(Customer.id == cid).first()
        if not c:
            skipped.append({"id": cid, "reason": "not_found"}); continue
        if db.query(Order).filter(Order.customer_id == cid).count() > 0:
            skipped.append({"id": cid, "reason": "has_orders"}); continue
        db.delete(c); deleted.append(cid)
    db.commit()
    return {"deleted": deleted, "skipped": skipped}


# ─── Product ───────────────────────────────────────────────────────────

def create_product(db, *, category=None, status=None, price=None, cost=None, stock=None) -> Dict[str, Any]:
    cat = _enum_or_random(CategoryEnum, category)
    seq = db.query(Product).filter(Product.category == cat).count() + 1
    p = Product(
        product_name=f"{cat.value}商品{seq}",
        category=cat,
        price=Decimal(str(price)) if price else Decimal(random.uniform(10, 500)).quantize(Decimal("0.01")),
        cost=Decimal(str(cost)) if cost else Decimal(random.uniform(5, 250)).quantize(Decimal("0.01")),
        stock=int(stock) if stock is not None else random.randint(50, 500),
        low_stock_threshold=random.randint(10, 50),
        status=_enum_or_random(ProductStatusEnum, status) if status else ProductStatusEnum.on_sale,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return _ser_product(p)


def update_product(db, id, **fields):
    """update_product 可能触发 stock_alert。返回:
    {"row": product_dict, "notif": notif_dict | None}
    或 None(未找到)。
    """
    p = db.query(Product).filter(Product.id == id).first()
    if not p:
        return None
    if "product_name" in fields and fields["product_name"]:
        p.product_name = fields["product_name"]
    if fields.get("category"):
        p.category = CategoryEnum(fields["category"])
    if fields.get("status"):
        p.status = ProductStatusEnum(fields["status"])
    if fields.get("price") is not None:
        p.price = Decimal(str(fields["price"]))
    if fields.get("cost") is not None:
        p.cost = Decimal(str(fields["cost"]))
    if fields.get("stock") is not None:
        p.stock = max(0, int(fields["stock"]))
    if fields.get("low_stock_threshold") is not None:
        p.low_stock_threshold = max(0, int(fields["low_stock_threshold"]))

    notif: Optional[Dict[str, Any]] = None
    cleared: List[int] = []
    if p.stock < p.low_stock_threshold:
        notif = _push_stock_alert(db, p)
    else:
        # 库存恢复到阈值以上 → 清理该商品现存的库存预警通知
        cleared = _clear_stock_alerts(db, p.product_name)

    db.commit()
    db.refresh(p)
    return {"row": _ser_product(p), "notif": notif, "cleared_notif_ids": cleared}


def delete_product(db, id) -> Union[Dict[str, Any], str, None]:
    p = db.query(Product).filter(Product.id == id).first()
    if not p:
        return None
    if db.query(OrderItem).filter(OrderItem.product_id == id).count() > 0:
        return "in_use"
    info = _ser_product(p)
    db.delete(p)
    db.commit()
    return info


def delete_products(db, ids: List[int]) -> Dict[str, Any]:
    """批量删除商品。被订单引用的跳过。"""
    deleted: List[int] = []
    skipped: List[Dict[str, Any]] = []
    for pid in ids:
        p = db.query(Product).filter(Product.id == pid).first()
        if not p:
            skipped.append({"id": pid, "reason": "not_found"}); continue
        if db.query(OrderItem).filter(OrderItem.product_id == pid).count() > 0:
            skipped.append({"id": pid, "reason": "in_use"}); continue
        db.delete(p); deleted.append(pid)
    db.commit()
    return {"deleted": deleted, "skipped": skipped}


# ─── Order ─────────────────────────────────────────────────────────────

def create_order(db, *, status=None, customer_id=None):
    """创建订单 + 随机 1-3 件 order_items。按初始 status 落对应 finance:
      - status >= paid     → sales_income + product_cost + ad_cost
      - status >= shipped  → 额外 + logistics_cost
    pending / cancelled / refunded 不落 finance。

    返回:{"row": order_dict, "finance": [...] | None, "notifs": [库存预警 dict, ...]}
    customer/产品不足时返回 None。
    """
    if customer_id:
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
    else:
        cust_total = db.query(Customer).count()
        if cust_total == 0:
            return None
        customer = db.query(Customer).offset(random.randint(0, cust_total - 1)).first()
    if not customer:
        return None

    products = db.query(Product).filter(Product.status == ProductStatusEnum.on_sale).all()
    if not products:
        return None

    now = _now()
    seq = db.query(Order).count() + 1
    # 订单生命周期建模:
    #   pending → {paid, cancelled}
    #   paid    → {shipped → completed, cancelled}
    # 一次性按真实分布加权抽取最终状态。只有 completed 才计入财务收入。
    order_status = _enum_or_random(OrderStatusEnum, status) if status else random.choices(
        [
            OrderStatusEnum.pending,    # 刚下单,未支付
            OrderStatusEnum.paid,       # 已支付,未发货
            OrderStatusEnum.shipped,    # 已发货,未签收
            OrderStatusEnum.completed,  # 已完成 — 唯一收入来源
            OrderStatusEnum.cancelled,  # 已取消(pending 或 paid 转入)
        ],
        weights=[15, 15, 15, 45, 10],
    )[0]
    order = Order(
        order_no=f"ORD{now.strftime('%Y%m%d')}{seq:05d}",
        customer_id=customer.id,
        total_amount=Decimal("0.00"),
        status=order_status,
        created_at=now,
    )
    db.add(order)
    db.flush()

    # cancelled 订单不扣库存(模拟"取消后归还库存")
    deduct_stock = order_status != OrderStatusEnum.cancelled
    subtotal_sum = Decimal("0.00")
    touched_products: Dict[int, Product] = {}
    for _ in range(random.randint(1, 3)):
        product = random.choice(products)
        qty = random.randint(1, 4)
        sub = (product.price * qty).quantize(Decimal("0.01"))
        db.add(OrderItem(
            order_id=order.id, product_id=product.id,
            quantity=qty, unit_price=product.price, subtotal=sub,
        ))
        subtotal_sum += sub
        if deduct_stock:
            product.stock = max(0, product.stock - qty)
            touched_products[product.id] = product

    order.total_amount = subtotal_sum
    # paid_at 写入条件:已经经过"支付"环节(paid/shipped/completed),
    # cancelled 30% 概率是 paid → cancelled(曾经支付过)
    if order.status in (OrderStatusEnum.paid, OrderStatusEnum.shipped, OrderStatusEnum.completed):
        order.paid_at = now
    elif order.status == OrderStatusEnum.cancelled and random.random() < 0.3:
        order.paid_at = now

    finance: List[Dict[str, Any]] = []
    if order.status in (OrderStatusEnum.paid, OrderStatusEnum.shipped, OrderStatusEnum.completed):
        finance.extend(_add_sale_finance(db, order))
    if order.status in (OrderStatusEnum.shipped, OrderStatusEnum.completed):
        finance.extend(_add_logistics_finance(db, order))
    if order.status == OrderStatusEnum.completed:
        order.completed_at = now

    # 扣库存后逐商品检查阈值,跌破则落一条 stock_alert 通知
    notifs: List[Dict[str, Any]] = []
    for p in touched_products.values():
        n = _push_stock_alert(db, p)
        if n:
            notifs.append(n)

    # 异常订单检测(大额 / 同客户高频)
    n_order = _push_order_alert(db, order, customer)
    if n_order:
        notifs.append(n_order)

    # 销售额波动检测 — 仅当此单已实际计入销售额(paid+)时才扫
    if order.status in (OrderStatusEnum.paid, OrderStatusEnum.shipped, OrderStatusEnum.completed):
        n_sales = _push_sales_alert(db)
        if n_sales:
            notifs.append(n_sales)

    db.commit()
    db.refresh(order)
    return {"row": _ser_order(order), "finance": finance or None, "notifs": notifs}


def update_order(db, id, *, status=None):
    """订单状态变更。按状态机转移同步 finance_records。受 ALLOWED_ORDER_TRANSITIONS 状态机约束。

    finance 同步规则(新):
      - pending → paid     : 写入 sales_income + product_cost + ad_cost,顺手扫 sales_alert
      - paid    → shipped  : 写入 logistics_cost
      - paid    → refunded : 写入 refund_out 支出(保留原 sales_income 等,资金已收过)+ 推 refund_alert
      - shipped → completed: 无新增(已就位)

    返回:
      - {"row": ..., "finance_added": [...] | None, "finance_removed": int, "notif": dict | None} 成功
      - None 订单不存在
      - "invalid_transition" 字符串 当前 status 不允许转到 new_status
    """
    o = db.query(Order).filter(Order.id == id).first()
    if not o:
        return None
    if not status:
        return {"row": _ser_order(o), "finance_added": None, "finance_removed": 0, "notif": None}

    new_status = OrderStatusEnum(status)
    # 状态机校验:只允许 ALLOWED_ORDER_TRANSITIONS 中预定义的路径;不变 status 直接放行
    if new_status != o.status:
        if new_status not in ALLOWED_ORDER_TRANSITIONS.get(o.status, set()):
            return "invalid_transition"

    old_status = o.status
    now = _now()

    o.status = new_status
    if new_status in (OrderStatusEnum.paid, OrderStatusEnum.shipped, OrderStatusEnum.completed) and not o.paid_at:
        o.paid_at = now
    if new_status == OrderStatusEnum.completed:
        o.completed_at = now
    elif old_status == OrderStatusEnum.completed and new_status != OrderStatusEnum.completed:
        # 终态理论上不可回退,这里只是防御性兜底
        o.completed_at = None

    finance_added: List[Dict[str, Any]] = []
    finance_removed = 0
    notif: Optional[Dict[str, Any]] = None

    if old_status == OrderStatusEnum.pending and new_status == OrderStatusEnum.paid:
        finance_added.extend(_add_sale_finance(db, o))
        # 销售额已实际入账,扫一次当日波动
        notif = _push_sales_alert(db)
    elif old_status == OrderStatusEnum.paid and new_status == OrderStatusEnum.shipped:
        finance_added.extend(_add_logistics_finance(db, o))
    elif old_status == OrderStatusEnum.paid and new_status == OrderStatusEnum.refunded:
        finance_added.extend(_add_refund_finance(db, o))
        notif = _push_refund_alert(db, o, o.total_amount or Decimal("0"))

    db.commit()
    db.refresh(o)
    return {
        "row": _ser_order(o),
        "finance_added": finance_added or None,
        "finance_removed": finance_removed,
        "notif": notif,
    }


def delete_order(db, id) -> Optional[Dict[str, Any]]:
    o = db.query(Order).filter(Order.id == id).first()
    if not o:
        return None
    db.query(FinanceRecord).filter(FinanceRecord.related_order_id == o.id).delete()
    db.query(Refund).filter(Refund.order_id == o.id).delete()
    info = _ser_order(o)
    db.delete(o)  # cascade order_items
    db.commit()
    return info


def delete_orders(db, ids: List[int]) -> Dict[str, Any]:
    """批量删除订单。同 single delete:级联清理 finance / refund / order_items。"""
    deleted: List[int] = []
    skipped: List[Dict[str, Any]] = []
    for oid in ids:
        o = db.query(Order).filter(Order.id == oid).first()
        if not o:
            skipped.append({"id": oid, "reason": "not_found"}); continue
        db.query(FinanceRecord).filter(FinanceRecord.related_order_id == oid).delete()
        db.query(Refund).filter(Refund.order_id == oid).delete()
        db.delete(o)  # cascade order_items via FK
        deleted.append(oid)
    db.commit()
    return {"deleted": deleted, "skipped": skipped}


# ─── Refund ────────────────────────────────────────────────────────────

def create_refund(db, *, order_id=None, amount=None):
    """从未退款的 completed 订单中创建退款。返回:
    {"row": refund_dict, "notif": notif_dict | None}
    无可用订单返回 None。
    """
    if order_id:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order or order.status != OrderStatusEnum.completed:
            return None
        if db.query(Refund).filter(Refund.order_id == order.id).count() > 0:
            return None
    else:
        refunded_ids = {r.order_id for r in db.query(Refund.order_id).all()}
        q = db.query(Order).filter(Order.status == OrderStatusEnum.completed)
        if refunded_ids:
            q = q.filter(~Order.id.in_(refunded_ids))
        candidates = q.all()
        if not candidates:
            return None
        order = random.choice(candidates)

    amt = (
        Decimal(str(amount)) if amount
        else (order.total_amount * Decimal(random.uniform(0.3, 1.0))).quantize(Decimal("0.01"))
    )
    now = _now()
    r = Refund(
        order_id=order.id,
        refund_amount=amt,
        reason=random.choice(list(RefundReasonEnum)),
        status=RefundStatusEnum.processing,
        created_at=now,
    )
    db.add(r)
    db.flush()

    notif = _push_refund_alert(db, order, amt)

    db.commit()
    db.refresh(r)
    return {"row": _ser_refund(r), "notif": notif}


def update_refund(db, id, **fields):
    r = db.query(Refund).filter(Refund.id == id).first()
    if not r:
        return None
    if fields.get("status"):        r.status = RefundStatusEnum(fields["status"])
    if fields.get("reason"):        r.reason = RefundReasonEnum(fields["reason"])
    if fields.get("refund_amount") is not None: r.refund_amount = Decimal(str(fields["refund_amount"]))
    if r.status == RefundStatusEnum.completed and not r.completed_at:
        r.completed_at = _now()
    db.commit()
    db.refresh(r)
    return _ser_refund(r)


def delete_refund(db, id) -> Optional[Dict[str, Any]]:
    r = db.query(Refund).filter(Refund.id == id).first()
    if not r:
        return None
    info = _ser_refund(r)
    db.delete(r)
    db.commit()
    return info


# ─── Finance ───────────────────────────────────────────────────────────

def create_finance_record(db, *, type_=None, category=None, amount=None) -> Dict[str, Any]:
    t = _enum_or_random(FinanceTypeEnum, type_)
    if category:
        try:
            c = FinanceCategoryEnum(category)
        except ValueError:
            c = None
    else:
        c = None
    if c is None:
        c = (
            FinanceCategoryEnum.sales_income if t == FinanceTypeEnum.income
            else random.choice([
                FinanceCategoryEnum.logistics_cost,
                FinanceCategoryEnum.ad_cost,
                FinanceCategoryEnum.refund_out,
            ])
        )
    amt = Decimal(str(amount)) if amount else Decimal(random.uniform(100, 10000))
    amt = amt.quantize(Decimal("0.01"))
    fr = FinanceRecord(
        type=t, category=c, amount=amt, related_order_id=None, recorded_at=_now(),
    )
    db.add(fr)
    db.commit()
    db.refresh(fr)
    return _ser_finance(fr)


def update_finance_record(db, id, **fields) -> Optional[Dict[str, Any]]:
    f = db.query(FinanceRecord).filter(FinanceRecord.id == id).first()
    if not f:
        return None
    if fields.get("type"):     f.type = FinanceTypeEnum(fields["type"])
    if fields.get("category"): f.category = FinanceCategoryEnum(fields["category"])
    if fields.get("amount") is not None: f.amount = Decimal(str(fields["amount"]))
    db.commit()
    db.refresh(f)
    return _ser_finance(f)


def delete_finance_record(db, id) -> Optional[Dict[str, Any]]:
    f = db.query(FinanceRecord).filter(FinanceRecord.id == id).first()
    if not f:
        return None
    info = _ser_finance(f)
    db.delete(f)
    db.commit()
    return info


# ─── Notification ──────────────────────────────────────────────────────

_NOTIF_TITLES = {
    "stock_alert":  "库存预警",
    "refund_alert": "大额退款",
    "order_alert":  "异常订单",
    "sales_alert":  "销售额波动",
}
_NOTIF_DEFAULT_CONTENT = {
    "stock_alert":  "某商品库存跌破阈值,请补货",
    "refund_alert": "订单发生退款,需审核",
    "order_alert":  "检测到异常下单行为,请人工核查",
    "sales_alert":  "今日销售额异常波动",
}


def create_notification(db, *, ntype=None, title=None, content=None) -> Dict[str, Any]:
    if not ntype or ntype not in _NOTIF_TITLES:
        ntype = random.choice(list(_NOTIF_TITLES.keys()))
    n = Notification(
        type=NotificationTypeEnum(ntype),
        title=title or _NOTIF_TITLES[ntype],
        content=content or _NOTIF_DEFAULT_CONTENT[ntype],
        is_read=False,
        created_at=_now(),
    )
    db.add(n)
    db.commit()
    db.refresh(n)
    return _ser_notification(n)


def update_notification(db, id, **fields) -> Optional[Dict[str, Any]]:
    n = db.query(Notification).filter(Notification.id == id).first()
    if not n:
        return None
    if "is_read" in fields and fields["is_read"] is not None:
        n.is_read = bool(fields["is_read"])
    if fields.get("title"):   n.title = fields["title"]
    if fields.get("content"): n.content = fields["content"]
    db.commit()
    db.refresh(n)
    return _ser_notification(n)


def delete_notification(db, id) -> Optional[Dict[str, Any]]:
    n = db.query(Notification).filter(Notification.id == id).first()
    if not n:
        return None
    info = _ser_notification(n)
    db.delete(n)
    db.commit()
    return info
