from datetime import UTC, date, datetime, timedelta
from typing import Tuple, Optional, Any, Dict

# 注册超过此天数视为老客
NEW_CUSTOMER_DAYS = 15


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# 判断客户是否为老客（注册超过 NEW_CUSTOMER_DAYS 天）
def is_returning_customer(registered_at: Optional[datetime]) -> bool:
    if registered_at is None:
        return False
    return (utc_now() - registered_at) > timedelta(days=NEW_CUSTOMER_DAYS)


# 返回客户类型字符串：'new' 或 'returning'
def customer_type_label(registered_at: Optional[datetime]) -> str:
    return "returning" if is_returning_customer(registered_at) else "new"


# 获取新老客判定时间阈值，registered_at 小于此值即为老客
def new_customer_threshold() -> datetime:
    return utc_now() - timedelta(days=NEW_CUSTOMER_DAYS)


# 解析日期范围参数，返回 (start_date, end_date) 元组
def parse_date_range(
    date_range: str = "30",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Tuple[date, date]:
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
        try:
            days = int(date_range)
            return today - timedelta(days=days), today
        except ValueError:
            return today - timedelta(days=30), today


# 获取与当前时间段等长的上一时间段
def get_prev_period(start: date, end: date) -> Tuple[date, date]:
    duration = (end - start).days
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=duration)
    return prev_start, prev_end


# 统一成功响应格式
def success_response(data: Any = None, message: str = "success") -> Dict[str, Any]:
    return {"code": 200, "message": message, "data": data}


# 统一错误响应格式
def error_response(message: str = "error", code: int = 400) -> Dict[str, Any]:
    return {"code": code, "message": message, "data": None}
