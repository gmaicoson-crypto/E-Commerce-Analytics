from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    Enum as SQLEnum,
    ForeignKey,
    Text,
    DECIMAL,
    Index,
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from database import Base


class CategoryEnum(str, enum.Enum):
    clothing = "服装"
    electronics = "电子"
    food = "食品"
    home = "家居"
    beauty = "美妆"


class GenderEnum(str, enum.Enum):
    male = "male"
    female = "female"


class AgeGroupEnum(str, enum.Enum):
    age_18_24 = "18-24"
    age_25_34 = "25-34"
    age_35_44 = "35-44"
    age_45_plus = "45+"


class CustomerTypeEnum(str, enum.Enum):
    new = "new"
    returning = "returning"


class OrderStatusEnum(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    shipped = "shipped"
    completed = "completed"
    cancelled = "cancelled"  # pending/paid → cancelled,不计入收入
    refunded = "refunded"


class ProductStatusEnum(str, enum.Enum):
    on_sale = "on_sale"
    off_sale = "off_sale"


class RefundStatusEnum(str, enum.Enum):
    processing = "processing"
    completed = "completed"


class RefundReasonEnum(str, enum.Enum):
    quality = "quality"
    wrong_item = "wrong_item"
    no_reason = "no_reason"
    logistics = "logistics"


class FinanceTypeEnum(str, enum.Enum):
    income = "income"
    expense = "expense"


class FinanceCategoryEnum(str, enum.Enum):
    sales_income = "sales_income"
    product_cost = "product_cost"
    logistics_cost = "logistics_cost"
    ad_cost = "ad_cost"
    refund_out = "refund_out"


class PermissionActionEnum(str, enum.Enum):
    grant = "grant"
    revoke = "revoke"


class NotificationTypeEnum(str, enum.Enum):
    stock_alert = "stock_alert"
    refund_alert = "refund_alert"
    order_alert = "order_alert"
    sales_alert = "sales_alert"


# System Tables
class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime, nullable=True)


class AdminVerificationCode(Base):
    """管理员注册流程的邮箱验证码。10 分钟内有效,used_at 标记已使用。"""

    __tablename__ = "admin_verification_codes"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), nullable=False, index=True)
    code = Column(String(6), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime, nullable=True)


class Module(Base):
    __tablename__ = "modules"

    id = Column(Integer, primary_key=True, index=True)
    module_key = Column(String(50), unique=True, nullable=False, index=True)
    module_name = Column(String(50), nullable=False)
    description = Column(String(200), nullable=True)
    sort_order = Column(Integer, default=0)


class EmployeeModulePermission(Base):
    __tablename__ = "employee_module_permissions"
    __table_args__ = (Index("idx_employee_module", "employee_id", "module_id"),)

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    granted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    granted_by = Column(Integer, ForeignKey("admins.id"), nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    revoked_by = Column(Integer, ForeignKey("admins.id"), nullable=True)


class PermissionChangeLog(Base):
    __tablename__ = "permission_change_logs"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("admins.id"), nullable=False, index=True)
    target_user_id = Column(
        Integer, ForeignKey("employees.id"), nullable=False, index=True
    )
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=False)
    action = Column(SQLEnum(PermissionActionEnum), nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    remark = Column(String(200), nullable=True)


# Business Tables
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    product_name = Column(String(100), nullable=False)
    category = Column(SQLEnum(CategoryEnum), nullable=False, index=True)
    price = Column(DECIMAL(10, 2), nullable=False)
    cost = Column(DECIMAL(10, 2), nullable=False)
    stock = Column(Integer, default=0, index=True)
    low_stock_threshold = Column(Integer, default=10)
    status = Column(
        SQLEnum(ProductStatusEnum), default=ProductStatusEnum.on_sale, index=True
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    order_items = relationship("OrderItem", back_populates="product")


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False)
    gender = Column(SQLEnum(GenderEnum), nullable=False, index=True)
    age_group = Column(SQLEnum(AgeGroupEnum), nullable=False)
    province = Column(String(20), nullable=False, index=True)
    customer_type = Column(SQLEnum(CustomerTypeEnum), nullable=False, index=True)
    registered_at = Column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )

    orders = relationship("Order", back_populates="customer")


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        Index("idx_customer_status_created", "customer_id", "status", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    order_no = Column(String(32), unique=True, nullable=False, index=True)
    customer_id = Column(
        Integer, ForeignKey("customers.id"), nullable=False, index=True
    )
    total_amount = Column(DECIMAL(10, 2), nullable=False)
    status = Column(
        SQLEnum(OrderStatusEnum), default=OrderStatusEnum.pending, index=True
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    paid_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True, index=True)

    customer = relationship("Customer", back_populates="orders")
    order_items = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(DECIMAL(10, 2), nullable=False)
    subtotal = Column(DECIMAL(10, 2), nullable=False)

    order = relationship("Order", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")


class Refund(Base):
    __tablename__ = "refunds"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    refund_amount = Column(DECIMAL(10, 2), nullable=False)
    reason = Column(SQLEnum(RefundReasonEnum), nullable=False)
    status = Column(
        SQLEnum(RefundStatusEnum), default=RefundStatusEnum.processing, index=True
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)


class FinanceRecord(Base):
    __tablename__ = "finance_records"
    __table_args__ = (
        Index("idx_type_category_recorded", "type", "category", "recorded_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    type = Column(SQLEnum(FinanceTypeEnum), nullable=False, index=True)
    category = Column(SQLEnum(FinanceCategoryEnum), nullable=False, index=True)
    amount = Column(DECIMAL(10, 2), nullable=False)
    related_order_id = Column(
        Integer, ForeignKey("orders.id"), nullable=True, index=True
    )
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(SQLEnum(NotificationTypeEnum), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
