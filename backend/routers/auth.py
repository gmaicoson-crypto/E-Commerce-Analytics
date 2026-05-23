import re
import random
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import UTC, datetime, timedelta
from typing import Optional
from database import get_db
from auth import verify_password, create_access_token, hash_password
from dependencies import get_current_user
from models import (
    Admin,
    Employee,
    Module,
    EmployeeModulePermission,
    AdminVerificationCode,
)
from schemas import LoginRequest, SendCodeRequest, AdminRegisterRequest
from email_service import send_email
from utils import success_response

router = APIRouter()

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# 当前用户资料更新请求体
class MeUpdate(BaseModel):
    username: Optional[str] = Field(default=None, min_length=2, max_length=50)
    email: Optional[str] = Field(default=None, min_length=5, max_length=100)


# 修改密码请求体
class PasswordChange(BaseModel):
    old_password: str = Field(min_length=4, max_length=128)
    new_password: str = Field(min_length=4, max_length=128)


# 登录接口：支持邮箱或用户名，管理员和员工共用
@router.post("/login", response_model=dict)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    from sqlalchemy import or_

    user = None
    role = None
    ident = (request.username or "").strip()

    # 优先匹配管理员表
    admin = (
        db.query(Admin)
        .filter(or_(Admin.email == ident, Admin.username == ident))
        .first()
    )
    if admin:
        if verify_password(request.password, admin.password_hash) and admin.is_active:
            user = admin
            role = "admin"
            admin.last_login_at = utc_now()
            db.commit()

    # 再匹配员工表
    if not user:
        employee = (
            db.query(Employee)
            .filter(or_(Employee.email == ident, Employee.username == ident))
            .first()
        )
        if employee:
            if (
                verify_password(request.password, employee.password_hash)
                and employee.is_active
            ):
                user = employee
                role = "employee"
                employee.last_login_at = utc_now()
                db.commit()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # 签发 JWT
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "role": role,
            "table": "admins" if role == "admin" else "employees",
        }
    )

    # 获取员工权限列表
    permissions = None
    if role == "employee":
        perms = (
            db.query(Module)
            .join(
                EmployeeModulePermission,
                Module.id == EmployeeModulePermission.module_id,
            )
            .filter(
                EmployeeModulePermission.employee_id == user.id,
                EmployeeModulePermission.is_active == True,
            )
            .all()
        )
        permissions = [m.module_key for m in perms]
    elif role == "admin":
        modules = db.query(Module).all()
        permissions = [m.module_key for m in modules]

    # 员工角色映射为前端 'staff'
    frontend_role = "staff" if role == "employee" else role

    return success_response(
        {
            "token": access_token,
            "role": frontend_role,
            "user_id": user.id,
            "username": user.username,
            "expires_in": 86400,
            "permissions": permissions,
        }
    )


# 管理员注册：发送邮箱验证码（同邮箱 60 秒限频）
@router.post("/admin/send-code", response_model=dict)
async def admin_send_code(body: SendCodeRequest, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(400, "邮箱格式不正确")
    if db.query(Admin).filter(Admin.email == email).first():
        raise HTTPException(400, "该邮箱已注册")

    cutoff = utc_now() - timedelta(seconds=60)
    recent = (
        db.query(AdminVerificationCode)
        .filter(
            AdminVerificationCode.email == email,
            AdminVerificationCode.created_at >= cutoff,
        )
        .first()
    )
    if recent:
        raise HTTPException(429, "请求过于频繁，60 秒后重试")

    code = "".join(random.choices("0123456789", k=6))
    rec = AdminVerificationCode(
        email=email,
        code=code,
        expires_at=utc_now() + timedelta(minutes=10),
    )
    db.add(rec)
    db.commit()

    subject = "电商数据分析平台 · 管理员注册验证码"
    text = (
        f"您正在注册管理员账号，本次验证码是：\n\n"
        f"    {code}\n\n"
        f"10 分钟内有效。如非本人操作，请忽略本邮件。"
    )
    try:
        send_email(email, subject, text)
    except RuntimeError as e:
        db.delete(rec)
        db.commit()
        raise HTTPException(500, str(e))
    except Exception as e:
        db.delete(rec)
        db.commit()
        raise HTTPException(500, f"邮件发送失败：{e}")

    return success_response({"sent": True, "email": email, "expires_in": 600})


# 管理员注册：校验验证码后创建账号
@router.post("/admin/register", response_model=dict)
async def admin_register(body: AdminRegisterRequest, db: Session = Depends(get_db)):
    username = body.username.strip()
    email = body.email.strip().lower()

    if not EMAIL_RE.match(email):
        raise HTTPException(400, "邮箱格式不正确")
    if db.query(Admin).filter(Admin.username == username).first():
        raise HTTPException(400, "用户名已被注册")
    if db.query(Admin).filter(Admin.email == email).first():
        raise HTTPException(400, "邮箱已被注册")

    rec = (
        db.query(AdminVerificationCode)
        .filter(
            AdminVerificationCode.email == email,
            AdminVerificationCode.code == body.code,
            AdminVerificationCode.used_at.is_(None),
            AdminVerificationCode.expires_at >= utc_now(),
        )
        .order_by(AdminVerificationCode.id.desc())
        .first()
    )
    if not rec:
        raise HTTPException(400, "验证码无效或已过期")

    admin = Admin(
        username=username,
        password_hash=hash_password(body.password),
        email=email,
        is_active=True,
    )
    db.add(admin)
    rec.used_at = utc_now()
    db.commit()
    db.refresh(admin)
    return success_response(
        {"admin_id": admin.id, "username": admin.username, "email": admin.email}
    )


# 登出接口（JWT 无状态，仅返回成功）
@router.post("/logout", response_model=dict, dependencies=[Depends(get_current_user)])
async def logout():
    return success_response(message="Logged out successfully")


# 获取当前登录用户信息及权限列表
@router.get("/me", response_model=dict)
async def get_me(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    permissions = []

    if current_user.role == "admin":
        modules = db.query(Module).all()
        permissions = [m.module_key for m in modules]
    elif current_user.role == "employee":
        perms = (
            db.query(Module)
            .join(
                EmployeeModulePermission,
                Module.id == EmployeeModulePermission.module_id,
            )
            .filter(
                EmployeeModulePermission.employee_id == current_user.id,
                EmployeeModulePermission.is_active == True,
            )
            .all()
        )
        permissions = [m.module_key for m in perms]

    frontend_role = "staff" if current_user.role == "employee" else current_user.role

    user_info = {
        "user_id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": frontend_role,
    }

    if current_user.role == "employee":
        user_info["permissions"] = permissions

    return success_response(user_info)


# 根据 token 中 table 字段返回对应的 ORM 模型类
def _self_table_model(current_user):
    return Admin if current_user.table == "admins" else Employee


# 当前用户更新自己的用户名或邮箱
@router.patch("/me", response_model=dict)
async def update_me(
    body: MeUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    Model = _self_table_model(current_user)
    user = db.query(Model).filter(Model.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if body.username is not None and body.username != user.username:
        if (
            db.query(Model)
            .filter(Model.username == body.username, Model.id != user.id)
            .first()
        ):
            raise HTTPException(status_code=400, detail="用户名已存在")
        user.username = body.username

    if body.email is not None and body.email != user.email:
        if not EMAIL_RE.match(body.email):
            raise HTTPException(status_code=400, detail="邮箱格式不正确")
        if (
            db.query(Model)
            .filter(Model.email == body.email, Model.id != user.id)
            .first()
        ):
            raise HTTPException(status_code=400, detail="邮箱已存在")
        user.email = body.email

    db.commit()
    db.refresh(user)

    return success_response(
        {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "role": "staff" if current_user.role == "employee" else "admin",
        },
        message="资料更新成功",
    )


# 当前用户修改密码，需验证旧密码
@router.post("/me/password", response_model=dict)
async def change_password(
    body: PasswordChange,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    Model = _self_table_model(current_user)
    user = db.query(Model).filter(Model.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="原密码不正确")
    if body.old_password == body.new_password:
        raise HTTPException(status_code=400, detail="新密码不能与原密码相同")

    user.password_hash = hash_password(body.new_password)
    db.commit()

    return success_response({"user_id": user.id}, message="密码修改成功")
