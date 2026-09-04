"""用户管理接口：CRUD、启用/禁用、重置密码、分配角色、个人资料。"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from ..core.audit import record_log
from ..core.deps import client_ip, get_current_user, require_permission
from ..core.exceptions import BizError, ok
from ..database import get_db
from ..dao.user_dao import UserDao
from ..models import User
from ..schemas import (
    AssignRoleRequest,
    ResetPasswordRequest,
    StatusRequest,
    UserCreateRequest,
    UserUpdateRequest,
)
from ..services import user_service

router = APIRouter(prefix="/api/users", tags=["用户管理"])


def _to_out(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "phone": user.phone,
        "email": user.email,
        "avatar": user.avatar,
        "role_id": user.role_id,
        "role_code": user.role.code,
        "role_name": user.role.name,
        "status": user.status,
        "groups": [g.name for g in user.groups],
        "created_at": user.created_at.isoformat(),
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
    }


@router.get("")
def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    keyword: str = "",
    status: int | None = Query(None, ge=0, le=1),
    role_id: int | None = None,
    _: User = Depends(require_permission("user:list")),
    db: Session = Depends(get_db),
):
    items, total = UserDao.list_page(db, page, size, keyword, status, role_id)
    return ok({"total": total, "items": [_to_out(u) for u in items]})


@router.post("")
def create_user(
    req: UserCreateRequest,
    request: Request,
    operator: User = Depends(require_permission("user:create")),
    db: Session = Depends(get_db),
):
    user = user_service.create_user(db, operator, req.username, req.password, req.role_id, req.phone, req.email)
    record_log(db, "user.create", ip=client_ip(request), user_id=operator.id, username=operator.username,
               params={"target": req.username, "role_id": req.role_id})
    return ok(_to_out(user), message="创建成功")


@router.put("/me")
def update_me(
    req: UserUpdateRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """个人信息修改（所有登录用户可用）。"""
    UserDao.update_profile(db, user, phone=req.phone, email=req.email, avatar=req.avatar)
    record_log(db, "user.profile.update", ip=client_ip(request), user_id=user.id, username=user.username)
    return ok(_to_out(user))


@router.put("/{user_id}")
def update_user(
    user_id: int,
    req: UserUpdateRequest,
    request: Request,
    operator: User = Depends(require_permission("user:edit")),
    db: Session = Depends(get_db),
):
    target = UserDao.get_by_id(db, user_id)
    if target is None:
        raise BizError("用户不存在", status_code=404, code=4040)
    user_service.ensure_can_manage(operator, target)
    UserDao.update_profile(db, target, phone=req.phone, email=req.email, avatar=req.avatar)
    record_log(db, "user.edit", ip=client_ip(request), user_id=operator.id, username=operator.username,
               params={"target": target.username})
    return ok(_to_out(target))


@router.post("/{user_id}/status")
def set_status(
    user_id: int,
    req: StatusRequest,
    request: Request,
    operator: User = Depends(require_permission("user:status")),
    db: Session = Depends(get_db),
):
    target = UserDao.get_by_id(db, user_id)
    if target is None:
        raise BizError("用户不存在", status_code=404, code=4040)
    user_service.set_status(db, operator, target, req.status)
    action = "user.disable" if req.status == 0 else "user.enable"
    record_log(db, action, ip=client_ip(request), user_id=operator.id, username=operator.username,
               params={"target": target.username})
    return ok(message="禁用成功" if req.status == 0 else "启用成功")


@router.post("/{user_id}/reset-password")
def reset_password(
    user_id: int,
    req: ResetPasswordRequest,
    request: Request,
    operator: User = Depends(require_permission("user:reset_password")),
    db: Session = Depends(get_db),
):
    target = UserDao.get_by_id(db, user_id)
    if target is None:
        raise BizError("用户不存在", status_code=404, code=4040)
    user_service.reset_password(db, operator, target, req.new_password)
    record_log(db, "user.reset_password", ip=client_ip(request), user_id=operator.id, username=operator.username,
               params={"target": target.username})
    return ok(message="密码已重置，该用户需重新登录")


@router.put("/{user_id}/role")
def assign_role(
    user_id: int,
    req: AssignRoleRequest,
    request: Request,
    operator: User = Depends(require_permission("user:assign_role")),
    db: Session = Depends(get_db),
):
    target = UserDao.get_by_id(db, user_id)
    if target is None:
        raise BizError("用户不存在", status_code=404, code=4040)
    user_service.assign_role(db, operator, target, req.role_id)
    record_log(db, "user.assign_role", ip=client_ip(request), user_id=operator.id, username=operator.username,
               params={"target": target.username, "role_id": req.role_id})
    return ok(_to_out(target))


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    request: Request,
    operator: User = Depends(require_permission("user:delete")),
    db: Session = Depends(get_db),
):
    target = UserDao.get_by_id(db, user_id)
    if target is None:
        raise BizError("用户不存在", status_code=404, code=4040)
    user_service.delete_user(db, operator, target)
    record_log(db, "user.delete", ip=client_ip(request), user_id=operator.id, username=operator.username,
               params={"target": target.username})
    return ok(message="删除成功")
