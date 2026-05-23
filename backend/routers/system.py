import re
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
from database import get_db
from dependencies import require_admin
from auth import hash_password
from models import (
    Employee,
    Admin,
    Module,
    EmployeeModulePermission,
    PermissionChangeLog,
)
from utils import success_response, error_response

router = APIRouter()

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class EmployeeCreate(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    email: str = Field(min_length=5, max_length=100)
    password: str = Field(min_length=4, max_length=128)


class EmployeeUpdate(BaseModel):
    is_active: Optional[bool] = None


def _ser_employee(emp: Employee, permissions: list[str] | None = None) -> dict:
    return {
        "id": emp.id,
        "username": emp.username,
        "email": emp.email,
        "is_active": emp.is_active,
        "created_at": emp.created_at.isoformat() if emp.created_at else None,
        "last_login_at": emp.last_login_at.isoformat() if emp.last_login_at else None,
        "permissions": permissions or [],
    }


@router.get("/employees", response_model=dict, dependencies=[Depends(require_admin)])
async def list_employees(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=10000),
    db: Session = Depends(get_db),
):
    """Get all employees with pagination."""
    total = db.query(Employee).count()
    employees = (
        db.query(Employee)
        .order_by(Employee.created_at.desc(), Employee.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    emp_list = []
    for emp in employees:
        perms = (
            db.query(Module)
            .join(
                EmployeeModulePermission,
                Module.id == EmployeeModulePermission.module_id,
            )
            .filter(
                EmployeeModulePermission.employee_id == emp.id,
                EmployeeModulePermission.is_active == True,
            )
            .all()
        )

        emp_list.append(
            {
                "id": emp.id,
                "username": emp.username,
                "email": emp.email,
                "is_active": emp.is_active,
                "created_at": emp.created_at.isoformat() if emp.created_at else None,
                "last_login_at": (
                    emp.last_login_at.isoformat() if emp.last_login_at else None
                ),
                "permissions": [m.module_key for m in perms],
            }
        )

    return success_response(
        {
            "data": emp_list,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size,
            },
        }
    )


@router.get("/employees/{employee_id}", response_model=dict, dependencies=[Depends(require_admin)])
async def get_employee(
    employee_id: int, db: Session = Depends(get_db)
):
    """Get employee details with permissions."""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found"
        )

    perms = (
        db.query(Module)
        .join(EmployeeModulePermission, Module.id == EmployeeModulePermission.module_id)
        .filter(
            EmployeeModulePermission.employee_id == employee_id,
            EmployeeModulePermission.is_active == True,
        )
        .all()
    )

    emp_info = {
        "id": employee.id,
        "username": employee.username,
        "email": employee.email,
        "is_active": employee.is_active,
        "created_at": employee.created_at.isoformat() if employee.created_at else None,
        "last_login_at": (
            employee.last_login_at.isoformat() if employee.last_login_at else None
        ),
        "permissions": [m.module_key for m in perms],
    }

    return success_response(emp_info)


@router.post("/employees", response_model=dict, dependencies=[Depends(require_admin)])
async def create_employee(
    body: EmployeeCreate,
    db: Session = Depends(get_db),
):
    """Admin-only:新增员工账号。校验用户名/邮箱唯一,密码 hash 后落库。"""
    if not EMAIL_RE.match(body.email):
        raise HTTPException(status_code=400, detail="邮箱格式不正确")
    if db.query(Employee).filter(Employee.username == body.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    if db.query(Employee).filter(Employee.email == body.email).first():
        raise HTTPException(status_code=400, detail="邮箱已存在")

    emp = Employee(
        username=body.username,
        email=body.email,
        password_hash=hash_password(body.password),
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return success_response(_ser_employee(emp), message="员工创建成功")


@router.patch("/employees/{employee_id}", response_model=dict, dependencies=[Depends(require_admin)])
async def update_employee(
    employee_id: int,
    body: EmployeeUpdate,
    db: Session = Depends(get_db),
):
    """Admin-only:更新员工启用状态。"""
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    if body.is_active is not None:
        emp.is_active = body.is_active

    db.commit()
    db.refresh(emp)

    # 拼当前生效权限
    perm_keys = [
        m.module_key
        for m in db.query(Module)
        .join(EmployeeModulePermission, Module.id == EmployeeModulePermission.module_id)
        .filter(
            EmployeeModulePermission.employee_id == emp.id,
            EmployeeModulePermission.is_active == True,
        )
        .all()
    ]

    return success_response(_ser_employee(emp, perm_keys))


@router.patch("/employees/{employee_id}/permissions", response_model=dict)
async def update_employee_permissions(
    employee_id: int,
    request: dict,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Grant or revoke module permissions for an employee."""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found"
        )

    module_key = request.get("module_key")
    action = request.get("action")  # "grant" or "revoke"

    if not module_key or not action:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="module_key and action required",
        )

    if action not in ["grant", "revoke"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="action must be 'grant' or 'revoke'",
        )

    module = db.query(Module).filter(Module.module_key == module_key).first()

    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Module not found"
        )

    if action == "grant":
        # Check if permission already exists
        existing = (
            db.query(EmployeeModulePermission)
            .filter(
                EmployeeModulePermission.employee_id == employee_id,
                EmployeeModulePermission.module_id == module.id,
            )
            .first()
        )

        if existing:
            if existing.is_active:
                return error_response("Permission already granted", 400)
            else:
                # Reactivate revoked permission
                existing.is_active = True
                existing.revoked_at = None
                existing.revoked_by = None
        else:
            # Create new permission
            perm = EmployeeModulePermission(
                employee_id=employee_id,
                module_id=module.id,
                is_active=True,
                granted_at=datetime.utcnow(),
                granted_by=current_user.id,
            )
            db.add(perm)

    elif action == "revoke":
        existing = (
            db.query(EmployeeModulePermission)
            .filter(
                EmployeeModulePermission.employee_id == employee_id,
                EmployeeModulePermission.module_id == module.id,
                EmployeeModulePermission.is_active == True,
            )
            .first()
        )

        if not existing:
            return error_response("Permission not found or already revoked", 404)

        existing.is_active = False
        existing.revoked_at = datetime.utcnow()
        existing.revoked_by = current_user.id

    # Log the change
    log = PermissionChangeLog(
        admin_id=current_user.id,
        target_user_id=employee_id,
        module_id=module.id,
        action=action,
        changed_at=datetime.utcnow(),
    )
    db.add(log)
    db.commit()

    return success_response(
        {"action": action, "module_key": module_key, "employee_id": employee_id},
        message=f"Permission {action}ed successfully",
    )


@router.get("/modules", response_model=dict, dependencies=[Depends(require_admin)])
async def list_modules(db: Session = Depends(get_db)):
    """Get all available modules."""
    modules = db.query(Module).order_by(Module.sort_order).all()

    module_list = [
        {
            "id": m.id,
            "module_key": m.module_key,
            "module_name": m.module_name,
            "description": m.description,
            "sort_order": m.sort_order,
        }
        for m in modules
    ]

    return success_response(module_list)


@router.get("/permission-logs", response_model=dict, dependencies=[Depends(require_admin)])
async def get_permission_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=10000),
    db: Session = Depends(get_db),
):
    """Get permission change logs."""
    total = db.query(PermissionChangeLog).count()
    logs = (
        db.query(PermissionChangeLog)
        .order_by(PermissionChangeLog.changed_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    log_list = []
    for log in logs:
        admin = db.query(Admin).filter(Admin.id == log.admin_id).first()
        employee = db.query(Employee).filter(Employee.id == log.target_user_id).first()
        module = db.query(Module).filter(Module.id == log.module_id).first()

        log_list.append(
            {
                "id": log.id,
                "admin_username": admin.username if admin else "Unknown",
                "target_username": employee.username if employee else "Unknown",
                "module_key": module.module_key if module else "Unknown",
                "action": log.action,
                "changed_at": log.changed_at.isoformat() if log.changed_at else None,
                "remark": log.remark,
            }
        )

    return success_response(
        {
            "data": log_list,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size,
            },
        }
    )
