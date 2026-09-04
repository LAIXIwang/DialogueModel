"""RBAC 接口：角色维护、权限列表、角色-权限分配。"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..core.audit import record_log
from ..core.deps import client_ip, require_any_permission, require_permission
from ..core.exceptions import BizError, ok
from ..database import get_db
from ..dao.rbac_dao import PermissionDao, RoleDao
from ..models import Role, User
from ..schemas import AssignPermissionsRequest, RoleCreateRequest, RoleUpdateRequest
from ..services import role_service

router = APIRouter(prefix="/api/roles", tags=["角色权限"])
perm_router = APIRouter(prefix="/api/permissions", tags=["权限"])


def _to_out(role: Role, db: Session) -> dict:
    return {
        "id": role.id,
        "code": role.code,
        "name": role.name,
        "description": role.description,
        "user_count": RoleDao.user_count(db, role.id),
        "permission_ids": [p.id for p in role.permissions],
    }


@router.get("")
def list_roles(
    _: User = Depends(require_any_permission("role:list", "user:create", "user:assign_role")),
    db: Session = Depends(get_db),
):
    """角色列表：角色管理页使用；管理员创建用户/分配角色时也需要（无角色菜单权限）。"""
    return ok([_to_out(r, db) for r in RoleDao.list_all(db)])


@router.post("")
def create_role(
    req: RoleCreateRequest,
    request: Request,
    operator: User = Depends(require_permission("role:create")),
    db: Session = Depends(get_db),
):
    role = role_service.create_role(db, req.code, req.name, req.description)
    record_log(db, "role.create", ip=client_ip(request), user_id=operator.id, username=operator.username,
               params={"code": req.code, "name": req.name})
    return ok(_to_out(role, db), message="创建成功")


@router.put("/{role_id}")
def update_role(
    role_id: int,
    req: RoleUpdateRequest,
    request: Request,
    operator: User = Depends(require_permission("role:edit")),
    db: Session = Depends(get_db),
):
    role = RoleDao.get_by_id(db, role_id)
    if role is None:
        raise BizError("角色不存在", status_code=404, code=4040)
    role_service.update_role(db, role, req.name, req.description)
    record_log(db, "role.edit", ip=client_ip(request), user_id=operator.id, username=operator.username,
               params={"role": role.code})
    return ok(_to_out(role, db))


@router.delete("/{role_id}")
def delete_role(
    role_id: int,
    request: Request,
    operator: User = Depends(require_permission("role:delete")),
    db: Session = Depends(get_db),
):
    role = RoleDao.get_by_id(db, role_id)
    if role is None:
        raise BizError("角色不存在", status_code=404, code=4040)
    role_service.delete_role(db, role)
    record_log(db, "role.delete", ip=client_ip(request), user_id=operator.id, username=operator.username,
               params={"role": role.code})
    return ok(message="删除成功")


@router.get("/{role_id}/permissions")
def get_role_permissions(
    role_id: int,
    _: User = Depends(require_permission("role:list")),
    db: Session = Depends(get_db),
):
    role = RoleDao.get_by_id(db, role_id)
    if role is None:
        raise BizError("角色不存在", status_code=404, code=4040)
    return ok([p.id for p in role.permissions])


@router.put("/{role_id}/permissions")
def set_role_permissions(
    role_id: int,
    req: AssignPermissionsRequest,
    request: Request,
    operator: User = Depends(require_permission("role:assign_permission")),
    db: Session = Depends(get_db),
):
    role = RoleDao.get_by_id(db, role_id)
    if role is None:
        raise BizError("角色不存在", status_code=404, code=4040)
    role_service.assign_permissions(db, role, req.permission_ids)
    record_log(db, "role.assign_permission", ip=client_ip(request), user_id=operator.id, username=operator.username,
               params={"role": role.code, "permission_ids": req.permission_ids})
    return ok(message="权限已更新")


@perm_router.get("")
def list_permissions(_: User = Depends(require_permission("permission:list")), db: Session = Depends(get_db)):
    """全部权限列表（供角色分配权限时勾选，按模块分组）。"""
    items = [
        {"id": p.id, "code": p.code, "name": p.name, "module": p.module}
        for p in PermissionDao.list_all(db)
    ]
    return ok(items)
