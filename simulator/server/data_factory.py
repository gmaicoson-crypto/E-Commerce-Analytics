"""Simulator data generator.

This module owns demo/random data generation. It never writes ecommerce_db
directly; generated payloads are sent to backend ingest APIs.
"""
from __future__ import annotations

import random
import threading
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import backend_client as backend


_clock = threading.local()


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
ORDER_STATUSES = ["pending", "paid", "shipped", "completed", "cancelled"]
FINANCE_TYPES = ["income", "expense"]
FINANCE_CATEGORIES = ["sales_income", "product_cost", "logistics_cost", "ad_cost"]
NOTIF_TYPES = ["stock_alert", "order_alert", "sales_alert"]


def _now() -> datetime:
    return getattr(_clock, "override", None) or datetime.utcnow()


def set_clock_override(ts: Optional[datetime]) -> None:
    _clock.override = ts


def _ts() -> str:
    return _now().isoformat()


def _pick(options, value=None):
    return value if value in options else random.choice(options)


def _money(value=None, low=10, high=500) -> float:
    if value is not None:
        return float(value)
    return float(Decimal(str(random.uniform(low, high))).quantize(Decimal("0.01")))


def get_counts(_db=None) -> Dict[str, int]:
    return backend.get_counts()


def sweep_stale_stock_alerts(_db=None) -> List[int]:
    return []


def list_customers(_db=None, page=1, page_size=20, *, gender=None, age_group=None, province=None, customer_type=None):
    return backend.list_customers(page=page, page_size=page_size, gender=gender, age_group=age_group, province=province, customer_type=customer_type)


def list_products(_db=None, page=1, page_size=20, *, category=None, status=None):
    return backend.list_products(page=page, page_size=page_size, category=category, status=status)


def list_orders(_db=None, page=1, page_size=20, *, status=None):
    return backend.list_orders(page=page, page_size=page_size, status=status)


def list_refunds(_db=None, page=1, page_size=20, *, status=None):
    return {"data": [], "pagination": {"page": page, "page_size": page_size, "total": 0, "total_pages": 0}}


def list_finance_records(_db=None, page=1, page_size=20, *, type_=None, category=None):
    return backend.list_finance(page=page, page_size=page_size, type=type_, category=category)


def list_notifications(_db=None, page=1, page_size=20, *, ntype=None, is_read=None):
    return backend.list_notifications(page=page, page_size=page_size, ntype=ntype, is_read=is_read)


def create_customer(_db=None, *, gender=None, age_group=None, province=None, customer_type=None) -> Dict[str, Any]:
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


def update_customer(_db, id, **fields):
    return backend.update_customer(id, fields)


def delete_customer(_db, id):
    return backend.delete_customer(id)


def delete_customers(_db, ids: List[int]):
    return backend.delete_customers(ids)


def create_product(_db=None, *, category=None, status=None, price=None, cost=None, stock=None) -> Dict[str, Any]:
    cat = _pick(CATEGORIES, category)
    seed = random.randint(10000, 99999)
    product_price = _money(price, 10, 500)
    product_cost = float(Decimal(str(cost if cost is not None else product_price * random.uniform(0.35, 0.7))).quantize(Decimal("0.01")))
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


def update_product(_db, id, **fields):
    row = backend.update_product(id, fields)
    return {"row": row, "notif": None, "cleared_notif_ids": []}


def delete_product(_db, id):
    try:
        return backend.delete_product(id)
    except RuntimeError as exc:
        msg = str(exc).lower()
        if "not found" in msg:
            return None
        if "used by orders" in msg:
            return "in_use"
        raise


def delete_products(_db, ids: List[int]):
    return backend.delete_products(ids)


def _available_customers():
    return backend.list_customers(page=1, page_size=100).get("data") or []


def _available_products():
    return backend.list_products(page=1, page_size=100, status="on_sale").get("data") or []


def create_order(_db=None, *, status=None, customer_id=None):
    customers = _available_customers()
    products = _available_products()
    if not customers or not products:
        return None
    customer = next((c for c in customers if c["id"] == customer_id), None) if customer_id else random.choice(customers)
    if not customer:
        return None
    chosen = random.sample(products, k=min(len(products), random.randint(1, 3)))
    items = [{"product_id": p["id"], "quantity": random.randint(1, 4)} for p in chosen]
    payload = {
        "customer_id": customer["id"],
        "items": items,
        "status": status or "pending",
        "created_at": _ts(),
    }
    return backend.create_order(payload)


def update_order(_db, id, *, status=None):
    return backend.update_order_status(id, status)


def delete_order(_db, id):
    return backend.delete_order(id)


def delete_orders(_db, ids: List[int]):
    return backend.delete_orders(ids)


def create_refund(_db=None, *, order_id=None, amount=None):
    return None


def update_refund(_db, id, **fields):
    return None


def delete_refund(_db, id):
    return None


def create_finance_record(_db=None, *, type_=None, category=None, amount=None) -> Dict[str, Any]:
    finance_type = _pick(FINANCE_TYPES, type_)
    valid_categories = ["sales_income"] if finance_type == "income" else ["product_cost", "logistics_cost", "ad_cost"]
    payload = {
        "type": finance_type,
        "category": category if category in valid_categories else random.choice(valid_categories),
        "amount": _money(amount, 100, 10000),
        "recorded_at": _ts(),
    }
    return backend.create_finance(payload)


def update_finance_record(_db, id, **fields):
    return backend.update_finance(id, fields)


def delete_finance_record(_db, id):
    return backend.delete_finance(id)


def create_notification(_db=None, *, ntype=None, title=None, content=None) -> Dict[str, Any]:
    notification_type = _pick(NOTIF_TYPES, ntype)
    payload = {
        "ntype": notification_type,
        "title": title or {"stock_alert": "库存预警", "order_alert": "异常订单", "sales_alert": "销售波动"}[notification_type],
        "content": content or "模拟平台产生的业务提醒",
        "created_at": _ts(),
    }
    return backend.create_notification(payload)


def update_notification(_db, id, **fields):
    return backend.update_notification(id, fields)


def delete_notification(_db, id):
    return backend.delete_notification(id)
