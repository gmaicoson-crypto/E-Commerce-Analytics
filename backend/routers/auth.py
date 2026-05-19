import re
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
from database import get_db
from auth import verify_password, create_access_token, hash_password
from dependencies import get_current_user
from models import Admin, Employee, Module, EmployeeModulePermission
from schemas import LoginRequest
from utils import success_response

router = APIRouter()

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class MeUpdate(BaseModel):
    username: Optional[str] = Field(default=None, min_length=2, max_length=50)
    email: Optional[str] = Field(default=None, min_length=5, max_length=100)


class PasswordChange(BaseModel):
    old_password: str = Field(min_length=4, max_length=128)
    new_password: str = Field(min_length=4, max_length=128)


@router.post("/login", response_model=dict)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Login endpoint - check both admins and employees tables."""
    user = None
    role = None

    # Try admin table first
    admin = db.query(Admin).filter(Admin.username == request.username).first()
    if admin:
        if verify_password(request.password, admin.password_hash) and admin.is_active:
            user = admin
            role = "admin"
            admin.last_login_at = datetime.utcnow()
            db.commit()

    # Try employee table if not found
    if not user:
        employee = db.query(Employee).filter(Employee.username == request.username).first()
        if employee:
            if verify_password(request.password, employee.password_hash) and employee.is_active:
                user = employee
                role = "employee"
                employee.last_login_at = datetime.utcnow()
                db.commit()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    # Create JWT token
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "role": role,
            "table": "admins" if role == "admin" else "employees"
        }
    )

    # Get permissions (if employee)
    permissions = None
    if role == "employee":
        perms = db.query(Module).join(
            EmployeeModulePermission,
            Module.id == EmployeeModulePermission.module_id
        ).filter(
            EmployeeModulePermission.employee_id == user.id,
            EmployeeModulePermission.is_active == True
        ).all()
        permissions = [m.module_key for m in perms]
    elif role == "admin":
        modules = db.query(Module).all()
        permissions = [m.module_key for m in modules]

    # Map role to frontend expectation (employee -> staff)
    frontend_role = "staff" if role == "employee" else role

    response = success_response({
        "token": access_token,
        "role": frontend_role,
        "user_id": user.id,
        "username": user.username,
        "expires_in": 86400,
        "permissions": permissions
    })

    return response


@router.post("/logout", response_model=dict)
async def logout(current_user=Depends(get_current_user)):
    """Logout endpoint - JWT is stateless, just return success."""
    return success_response(message="Logged out successfully")


@router.get("/me", response_model=dict)
async def get_me(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user info with permissions."""
    permissions = []

    if current_user.role == "admin":
        modules = db.query(Module).all()
        permissions = [m.module_key for m in modules]
    elif current_user.role == "employee":
        perms = db.query(Module).join(
            EmployeeModulePermission,
            Module.id == EmployeeModulePermission.module_id
        ).filter(
            EmployeeModulePermission.employee_id == current_user.id,
            EmployeeModulePermission.is_active == True
        ).all()
        permissions = [m.module_key for m in perms]

    # Map role for frontend
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


def _self_table_model(current_user):
    """根据 token 的 table 字段返回该用户对应的 ORM model 类。"""
    return Admin if current_user.table == "admins" else Employee


@router.patch("/me", response_model=dict)
async def update_me(
    body: MeUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """当前用户更新自己的 username/email。两边都做唯一性校验。"""
    Model = _self_table_model(current_user)
    user = db.query(Model).filter(Model.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if body.username is not None and body.username != user.username:
        if db.query(Model).filter(Model.username == body.username, Model.id != user.id).first():
            raise HTTPException(status_code=400, detail="用户名已存在")
        user.username = body.username

    if body.email is not None and body.email != user.email:
        if not EMAIL_RE.match(body.email):
            raise HTTPException(status_code=400, detail="邮箱格式不正确")
        if db.query(Model).filter(Model.email == body.email, Model.id != user.id).first():
            raise HTTPException(status_code=400, detail="邮箱已存在")
        user.email = body.email

    db.commit()
    db.refresh(user)

    return success_response({
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "role": "staff" if current_user.role == "employee" else "admin",
    }, message="资料更新成功")


@router.post("/me/password", response_model=dict)
async def change_password(
    body: PasswordChange,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """当前用户修改自己的密码。必须验证旧密码。"""
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
