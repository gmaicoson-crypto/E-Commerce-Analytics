from pydantic import BaseModel, Field
from typing import List, Optional, Generic, TypeVar
from datetime import datetime


# Generic Response Wrapper
T = TypeVar('T')


class APIResponse(BaseModel, Generic[T]):
    code: int = 200
    message: str = "success"
    data: Optional[T] = None


# Auth Schemas
class LoginRequest(BaseModel):
    username: str
    password: str


class SendCodeRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=100)


class AdminRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6, max_length=100)
    code: str = Field(..., min_length=6, max_length=6)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: int
    username: str
    expires_in: int = 86400
    permissions: Optional[List[str]] = None


class UserInfo(BaseModel):
    user_id: int
    username: str
    email: str
    role: str
    permissions: Optional[List[str]] = None


# Pagination
class PaginatedData(BaseModel, Generic[T]):
    total: int
    page: int
    page_size: int
    list: List[T]


# Employee & Permission Schemas
class EmployeeCreate(BaseModel):
    username: str
    email: str
    password: str


class EmployeeUpdate(BaseModel):
    email: Optional[str] = None
    is_active: Optional[bool] = None


class PermissionInfo(BaseModel):
    module_key: str
    module_name: str
    is_active: bool
    granted_at: datetime
    granted_by: str
    revoked_at: Optional[datetime] = None
    revoked_by: Optional[str] = None


class EmployeeOut(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    created_at: datetime
    permissions: Optional[List[PermissionInfo]] = None


class PermissionUpdate(BaseModel):
    module_key: str
    action: str  # 'grant' or 'revoke'


class PermissionLogOut(BaseModel):
    id: int
    admin_username: str
    target_username: str
    module_name: str
    action: str
    changed_at: datetime
    remark: Optional[str] = None


# Sales Schemas
class KPIMetric(BaseModel):
    value: float
    yoy: float = 0.0  # year-over-year change rate


class SalesKPIOut(BaseModel):
    total_sales: float
    total_sales_yoy: float
    total_orders: int
    total_orders_yoy: float
    avg_order_value: float
    avg_order_value_yoy: float
    refund_rate: float
    refund_rate_yoy: float


class TrendPoint(BaseModel):
    date: str
    sales: float
    orders: int


class CategoryShare(BaseModel):
    category: str
    sales: float
    ratio: float


class ProvinceData(BaseModel):
    province: str
    sales: float


# Product Schemas
class ProductRankItem(BaseModel):
    rank: int
    product_id: int
    product_name: str
    category: str
    sales_count: int
    sales_amount: float


class InventoryWarning(BaseModel):
    product_id: int
    product_name: str
    category: str
    stock: int
    low_stock_threshold: int


class ProductListItem(BaseModel):
    product_id: int
    product_name: str
    category: str
    price: float
    stock: int
    low_stock_threshold: int
    sales_count: int
    status: str


class ProductSalesTrend(BaseModel):
    product_id: int
    product_name: str
    trend: List[dict]  # [{date, sales_count}, ...]


# User Schemas
class UserKPIOut(BaseModel):
    total_customers: int
    new_customers: int
    returning_customers: int
    total_customers_yoy: float = 0.0
    new_customers_yoy: float = 0.0
    returning_customers_yoy: float = 0.0


class TypeRatio(BaseModel):
    new: dict  # {count, ratio}
    returning: dict


class RegisterTrendPoint(BaseModel):
    date: str
    count: int


class ProvinceUserData(BaseModel):
    province: str
    count: int
    pct: float


class AgeGroupData(BaseModel):
    age_group: str
    count: int
    ratio: float


class GenderData(BaseModel):
    male: dict  # {count, ratio}
    female: dict


# Order Schemas
class OrderKPIOut(BaseModel):
    total_orders: int
    completed_orders: int
    refunded_orders: int
    avg_order_amount: float
    total_orders_yoy: float = 0.0
    completed_orders_yoy: float = 0.0
    refunded_orders_yoy: float = 0.0


class OrderStatusItem(BaseModel):
    status: str
    count: int
    ratio: float


class OrderTrendPoint(BaseModel):
    date: str
    count: int


class OrderListItem(BaseModel):
    order_no: str
    username: str
    total_amount: float
    status: str
    created_at: datetime


# Finance Schemas
class FinanceKPIOut(BaseModel):
    total_income: float
    total_expense: float
    net_profit: float
    profit_margin: float
    total_income_yoy: float = 0.0
    total_expense_yoy: float = 0.0
    net_profit_yoy: float = 0.0


class FinanceTrendPoint(BaseModel):
    date: str
    income: float
    expense: float


class ExpenseBreakdown(BaseModel):
    category: str
    label: str
    amount: float
    ratio: float


class FinanceRecordItem(BaseModel):
    id: int
    type: str
    category: str
    label: str
    amount: float
    related_order_no: Optional[str] = None
    recorded_at: datetime


# Notification Schemas
class NotificationOut(BaseModel):
    id: int
    type: str
    title: str
    content: str
    is_read: bool
    created_at: datetime


# AI Schemas
class AIChatRequest(BaseModel):
    message: str
    mode: str = "query"  # query, trend_analysis, navigation
    history: Optional[List[dict]] = None


class AIChatResponse(BaseModel):
    session_id: str


class AIStreamMessage(BaseModel):
    event: str  # 'token', 'action', 'done'
    data: dict
