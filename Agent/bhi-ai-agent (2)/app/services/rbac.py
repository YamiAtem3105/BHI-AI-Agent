"""Phân quyền 4 cấp: super_admin > admin > manager > member."""

from fastapi import Depends, HTTPException

from app.services.auth_token import get_current_user

ROLES = ("super_admin", "admin", "manager", "member")

ROLE_RANK = {
    "super_admin": 4,
    "admin": 3,
    "manager": 2,
    "member": 1,
}

# Quyền theo tính năng
PERMISSIONS = {
    "dashboard.view": ("manager", "admin", "super_admin"),
    "dashboard.work_pool.all": ("manager", "admin", "super_admin"),
    "dashboard.work_pool.self": ("member", "manager", "admin", "super_admin"),
    "dashboard.ai_organize": ("manager", "admin", "super_admin"),
    "data.read.all": ("admin", "super_admin"),
    "data.read.dept": ("manager", "admin", "super_admin"),
    "data.read.self": ("member", "manager", "admin", "super_admin"),
    "data.write.task": ("member", "manager", "admin", "super_admin"),
    "data.write.wbs": ("manager", "admin", "super_admin"),
    "users.manage": ("super_admin",),
    "messaging.field_report": ("member", "manager", "admin", "super_admin"),
}


def normalize_role(role: str | None) -> str:
    r = (role or "member").strip().lower()
    return r if r in ROLE_RANK else "member"


def has_permission(role: str, permission: str) -> bool:
    allowed = PERMISSIONS.get(permission, ())
    return normalize_role(role) in allowed


def role_at_least(role: str, minimum: str) -> bool:
    return ROLE_RANK.get(normalize_role(role), 0) >= ROLE_RANK.get(normalize_role(minimum), 0)


def require_permission(permission: str):
    """FastAPI dependency — raise 403 nếu thiếu quyền."""

    def _dep(user: dict = Depends(get_current_user)) -> dict:
        role = normalize_role(user.get("role"))
        if not has_permission(role, permission):
            raise HTTPException(
                status_code=403,
                detail=f"Vai trò '{role}' không có quyền '{permission}'.",
            )
        user["role"] = role
        return user

    return _dep


def can_view_staff_data(viewer_role: str, viewer_name: str, target_name: str) -> bool:
    """Kiểm tra viewer có được xem dữ liệu của target không."""
    role = normalize_role(viewer_role)
    if role in ("super_admin", "admin"):
        return True
    if role == "manager":
        return True
    if role == "member":
        return viewer_name == target_name
    return False
