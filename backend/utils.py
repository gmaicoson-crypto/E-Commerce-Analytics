from datetime import datetime, date, timedelta
from typing import Tuple, Optional, Any, Dict
from decimal import Decimal


# ─── 客户类型判定规则 ────────────────────────────────────────────────────
# 业务规则:注册即为新客,注册时间 > 30 天后自动转为老客。
# 判定基于 Customer.registered_at,与 DB 的 customer_type 字段无关
# (该字段保留向后兼容,但不再代表真理)。
NEW_CUSTOMER_DAYS = 15


def is_returning_customer(registered_at: Optional[datetime]) -> bool:
    """注册时间超过 NEW_CUSTOMER_DAYS 天即视为老客。"""
    if registered_at is None:
        return False
    return (datetime.utcnow() - registered_at) > timedelta(days=NEW_CUSTOMER_DAYS)


def customer_type_label(registered_at: Optional[datetime]) -> str:
    """返回 'new' / 'returning' 字符串,用于序列化输出。"""
    return "returning" if is_returning_customer(registered_at) else "new"


def new_customer_threshold() -> datetime:
    """SQL 比较用:registered_at < threshold 即为老客。"""
    return datetime.utcnow() - timedelta(days=NEW_CUSTOMER_DAYS)


def parse_date_range(date_range: str = "30", start_date: Optional[str] = None, end_date: Optional[str] = None) -> Tuple[date, date]:
    """Parse date_range parameter and return (start_date, end_date)."""
    today = date.today()

    if date_range == "today":
        return today, today
    elif date_range == "7":
        return today - timedelta(days=7), today
    elif date_range == "30":
        return today - timedelta(days=30), today
    elif date_range == "90":
        return today - timedelta(days=90), today
    elif date_range == "custom":
        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d").date()
                end = datetime.strptime(end_date, "%Y-%m-%d").date()
                return start, end
            except ValueError:
                return today - timedelta(days=30), today
        return today - timedelta(days=30), today
    else:
        # Try to parse as number of days
        try:
            days = int(date_range)
            return today - timedelta(days=days), today
        except ValueError:
            return today - timedelta(days=30), today


def get_prev_period(start: date, end: date) -> Tuple[date, date]:
    """Get the previous period with same duration."""
    duration = (end - start).days
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=duration)
    return prev_start, prev_end


def calc_change_rate(current: float, previous: float) -> float:
    """Calculate year-over-year change rate."""
    if previous == 0:
        return 0.0
    return round((current - previous) / abs(previous) * 100, 2)


def success_response(data: Any = None, message: str = "success") -> Dict[str, Any]:
    """Unified success response format."""
    return {
        "code": 200,
        "message": message,
        "data": data
    }


def error_response(message: str = "error", code: int = 400) -> Dict[str, Any]:
    """Unified error response format."""
    return {
        "code": code,
        "message": message,
        "data": None
    }


def paginate(items: list, total: int, page: int, page_size: int) -> Dict[str, Any]:
    """Format paginated response."""
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "list": items
    }


def decimal_to_float(val) -> float:
    """Convert Decimal to float, handle None."""
    if val is None:
        return 0.0
    if isinstance(val, Decimal):
        return float(val)
    return float(val)
