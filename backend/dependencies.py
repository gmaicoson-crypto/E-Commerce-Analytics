from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, Callable
from database import get_db
from auth import decode_access_token
from models import Admin, Employee, Module, EmployeeModulePermission

security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    """Extract and validate JWT token, return user object."""
    token = credentials.credentials
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    role = payload.get("role")
    table = payload.get("table")

    if not user_id or not role or not table:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if table == "admins":
        user = db.query(Admin).filter(Admin.id == int(user_id)).first()
    elif table == "employees":
        user = db.query(Employee).filter(Employee.id == int(user_id)).first()
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user table",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Attach extra info
    user.role = role
    user.table = table
    return user


def require_admin(current_user=Depends(get_current_user)):
    """Dependency to check if user is admin."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def check_module_permission(module_key: str) -> Callable:
    """Factory function to create a dependency that checks module permission."""
    async def verify_permission(
        current_user=Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        # Admin has access to all modules
        if current_user.role == "admin":
            return current_user

        # Employee: check permission_change_logs
        if current_user.role == "employee":
            module = db.query(Module).filter(Module.module_key == module_key).first()
            if not module:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Module not found"
                )

            permission = db.query(EmployeeModulePermission).filter(
                EmployeeModulePermission.employee_id == current_user.id,
                EmployeeModulePermission.module_id == module.id,
                EmployeeModulePermission.is_active == True
            ).first()

            if not permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Module access denied"
                )

        return current_user

    return verify_permission


def get_user_permissions(user_id: int, role: str, db: Session = Depends(get_db)) -> list:
    """Get list of module_keys that user has access to."""
    if role == "admin":
        # Admin has all permissions
        modules = db.query(Module).all()
        return [m.module_key for m in modules]
    elif role == "employee":
        perms = db.query(EmployeeModulePermission).filter(
            EmployeeModulePermission.employee_id == user_id,
            EmployeeModulePermission.is_active == True
        ).all()
        module_ids = [p.module_id for p in perms]
        modules = db.query(Module).filter(Module.id.in_(module_ids)).all()
        return [m.module_key for m in modules]
    return []
