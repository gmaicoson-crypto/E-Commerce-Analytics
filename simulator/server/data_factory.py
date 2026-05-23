from __future__ import annotations

import random
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List

import backend_client as backend

# 枚举常量：省份、品类、性别等业务枚举值
PROVINCES = [
    "北京", "上海", "天津", "重庆", "河北", "山西", "辽宁", "吉林", "黑龙江",
    "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南", "湖北", "湖南",
    "广东", "海南", "四川", "贵州", "云南", "陕西", "甘肃", "青海", "台湾",
    "内蒙古", "广西", "西藏", "宁夏", "新疆", "香港", "澳门",
]
CATEGORIES = ["服装", "电子", "食品", "家居", "美妆"]
GENDERS = ["male", "female"]
AGE_GROUPS = ["18-24", "25-34", "35-44", "45+"]
CUSTOMER_TYPES = ["new", "returning"]
PRODUCT_STATUSES = ["on_sale", "off_sale"]
FINANCE_TYPES = ["income", "expense"]
NOTIF_TYPES = ["stock_alert", "order_alert", "sales_alert"]


def _now() -> datetime:
    return datetime.utcnow()


def _ts() -> str:
    return _now().isoformat()


def _pick(options, value=None):
    # 若 value 合法则直接使用，否则随机选取
    return value if value in options else random.choice(options)


def _money(value=None, low=10, high=500) -> float:
    # 生成指定范围内的随机金额，保留两位小数
    if value is not None:
        return float(value)
    return float(Decimal(str(random.uniform(low, high))).quantize(Decimal("0.01")))


# ── 统计 ──────────────────────────────────────────────────────────────────

def get_counts() -> Dict[str, int]:
    return backend.get_counts()


def sweep_stale_stock_alerts() -> List[int]:
    # 清理过期库存预警，当前由后端负责，此处返回空列表
    return []


# ── 列表查询（直接透传后端） ───────────────────────────────────────────────

def list_customers(page=1, page_size=20, *, gender=None, age_group=None, province=None, customer_type=None):
    return backend.list_customers(
        page=page, page_size=page_size,
        gender=gender, age_group=age_group,
        province=province, customer_type=customer_type,
    )


def list_products(page=1, page_size=20, *, category=None, status=None):
    return backend.list_products(page=page, page_size=page_size, category=category, status=status)


def list_orders(page=1, page_size=20, *, status=None):
    return backend.list_orders(page=page, page_size=page_size, status=status)


def list_finance_records(page=1, page_size=20, *, type_=None, category=None):
    return backend.list_finance(page=page, page_size=page_size, type=type_, category=category)


def list_notifications(page=1, page_size=20, *, ntype=None, is_read=None):
    return backend.list_notifications(page=page, page_size=page_size, ntype=ntype, is_read=is_read)


# ── 客户 ──────────────────────────────────────────────────────────────────

def create_customer(*, gender=None, age_group=None, province=None, customer_type=None) -> Dict[str, Any]:
    seed = random.randint(10000, 99999)
    payload = {
        "username": f"customer_{seed}",
        "gender": _pick(GENDERS, gender),
        "age_group": _pick(AGE_GROUPS, age_group),
        "province": _pick(PROVINCES, province),
        "customer_type": _pick(CUSTOMER_TYPES, customer_type),
        "registered_at": _ts(),
    }
    return backend.create_customer(payload)


def update_customer(id, **fields):
    return backend.update_customer(id, fields)


def delete_customer(id):
    return backend.delete_customer(id)


def delete_customers(ids: List[int]):
    return backend.delete_customers(ids)


# ── 商品 ──────────────────────────────────────────────────────────────────

def create_product(*, category=None, status=None, price=None, cost=None, stock=None) -> Dict[str, Any]:
    cat = _pick(CATEGORIES, category)
    seed = random.randint(10000, 99999)
    product_price = _money(price, 10, 500)
    # 成本默认为售价的 35%～70%
    product_cost = float(
        Decimal(
            str(cost if cost is not None else product_price * random.uniform(0.35, 0.7))
        ).quantize(Decimal("0.01"))
    )
    payload = {
        "product_name": f"{cat}商品{seed}",
        "category": cat,
        "price": product_price,
        "cost": product_cost,
        "stock": int(stock if stock is not None else random.randint(50, 500)),
        "low_stock_threshold": random.randint(10, 50),
        "status": _pick(PRODUCT_STATUSES, status) if status else "on_sale",
        "created_at": _ts(),
    }
    return backend.create_product(payload)


def update_product(id, **fields):
    row = backend.update_product(id, fields)
    return {"row": row, "notif": None, "cleared_notif_ids": []}


def delete_product(id):
    try:
        return backend.delete_product(id)
    except RuntimeError as exc:
        msg = str(exc).lower()
        if "not found" in msg:
            return None
        if "used by orders" in msg:
            return "in_use"
        raise


def delete_products(ids: List[int]):
    return backend.delete_products(ids)


# ── 订单 ──────────────────────────────────────────────────────────────────

def _available_customers():
    return backend.list_customers(page=1, page_size=100).get("data") or []


def _available_products():
    return backend.list_products(page=1, page_size=100, status="on_sale").get("data") or []


def create_order(*, status=None, customer_id=None):
    customers = _available_customers()
    products = _available_products()
    if not customers or not products:
        return None
    # 优先使用指定客户，否则随机选取
    customer = (
        next((c for c in customers if c["id"] == customer_id), None)
        if customer_id
        else random.choice(customers)
    )
    if not customer:
        return None
    # 随机选 1～3 个商品组成订单明细
    chosen = random.sample(products, k=min(len(products), random.randint(1, 3)))
    items = [{"product_id": p["id"], "quantity": random.randint(1, 4)} for p in chosen]
    payload = {
        "customer_id": customer["id"],
        "items": items,
        "status": status or "pending",
        "created_at": _ts(),
    }
    return backend.create_order(payload)


def update_order(id, *, status=None):
    return backend.update_order_status(id, status)


def delete_order(id):
    return backend.delete_order(id)


def delete_orders(ids: List[int]):
    return backend.delete_orders(ids)


# ── 财务 ──────────────────────────────────────────────────────────────────

def create_finance_record(*, type_=None, category=None, amount=None) -> Dict[str, Any]:
    finance_type = _pick(FINANCE_TYPES, type_)
    # 根据收支类型确定合法分类
    valid_categories = (
        ["sales_income"]
        if finance_type == "income"
        else ["product_cost", "logistics_cost", "ad_cost"]
    )
    payload = {
        "type": finance_type,
        "category": (
            category if category in valid_categories else random.choice(valid_categories)
        ),
        "amount": _money(amount, 100, 10000),
        "recorded_at": _ts(),
    }
    return backend.create_finance(payload)


def update_finance_record(id, **fields):
    return backend.update_finance(id, fields)


def delete_finance_record(id):
    return backend.delete_finance(id)


# ── 通知 ──────────────────────────────────────────────────────────────────

def create_notification(*, ntype=None, title=None, content=None) -> Dict[str, Any]:
    notification_type = _pick(NOTIF_TYPES, ntype)
    payload = {
        "ntype": notification_type,
        "title": title or {
            "stock_alert": "库存预警",
            "order_alert": "异常订单",
            "sales_alert": "销售波动",
        }[notification_type],
        "content": content or "模拟平台产生的业务提醒",
        "created_at": _ts(),
    }
    return backend.create_notification(payload)


def update_notification(id, **fields):
    return backend.update_notification(id, fields)


def delete_notification(id):
    return backend.delete_notification(id)
