from __future__ import annotations

from typing import Dict, Optional
import os

import httpx


BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
BACKEND_INGEST_TOKEN = os.environ.get("BACKEND_INGEST_TOKEN")

_client = httpx.Client(timeout=10.0, trust_env=False)


def _headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {BACKEND_INGEST_TOKEN}"} if BACKEND_INGEST_TOKEN else {}


def request(method: str, path: str, *, params: Optional[dict] = None, json: Optional[dict] = None):
    res = _client.request(
        method,
        f"{BACKEND_URL}/api/ingest{path}",
        params={k: v for k, v in (params or {}).items() if v is not None},
        json=json,
        headers=_headers(),
    )
    payload = res.json() if res.content else {}
    if not res.is_success:
        detail = payload.get("detail") if isinstance(payload, dict) else None
        if isinstance(detail, dict):
            raise RuntimeError(detail.get("message") or str(detail))
        raise RuntimeError(payload.get("message") if isinstance(payload, dict) else f"HTTP {res.status_code}")
    return payload.get("data")


def get_counts():
    return request("GET", "/counts")


def list_customers(**params):
    return request("GET", "/customers/list", params=params)


def create_customer(payload: dict):
    return request("POST", "/customers", json=payload)


def update_customer(customer_id: int, payload: dict):
    return request("PATCH", f"/customers/{customer_id}", json=payload)


def delete_customer(customer_id: int):
    return request("DELETE", f"/customers/{customer_id}")


def delete_customers(ids: list[int]):
    return request("POST", "/customers/bulk-delete", json={"ids": ids})


def list_products(**params):
    return request("GET", "/products/list", params=params)


def create_product(payload: dict):
    return request("POST", "/products", json=payload)


def update_product(product_id: int, payload: dict):
    return request("PATCH", f"/products/{product_id}", json=payload)


def delete_product(product_id: int):
    return request("DELETE", f"/products/{product_id}")


def delete_products(ids: list[int]):
    return request("POST", "/products/bulk-delete", json={"ids": ids})


def list_orders(**params):
    return request("GET", "/orders/list", params=params)


def create_order(payload: dict):
    return request("POST", "/orders", json=payload)


def update_order_status(order_id: int, status: str):
    return request("PATCH", f"/orders/{order_id}/status", json={"status": status})


def delete_order(order_id: int):
    return request("DELETE", f"/orders/{order_id}")


def delete_orders(ids: list[int]):
    return request("POST", "/orders/bulk-delete", json={"ids": ids})


def list_finance(**params):
    return request("GET", "/finance/list", params=params)


def create_finance(payload: dict):
    return request("POST", "/finance", json=payload)


def update_finance(finance_id: int, payload: dict):
    return request("PATCH", f"/finance/{finance_id}", json=payload)


def delete_finance(finance_id: int):
    return request("DELETE", f"/finance/{finance_id}")


def list_notifications(**params):
    return request("GET", "/notifications/list", params=params)


def create_notification(payload: dict):
    return request("POST", "/notifications", json=payload)


def update_notification(notification_id: int, payload: dict):
    return request("PATCH", f"/notifications/{notification_id}", json=payload)


def delete_notification(notification_id: int):
    return request("DELETE", f"/notifications/{notification_id}")
