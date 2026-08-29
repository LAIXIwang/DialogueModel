"""分组管理接口：分组 CRUD、成员批量分配、权限统一分配。"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..core.audit import record_log
from ..core.deps import client_ip, require_permission
from ..core.exceptions import BizError, ok
from ..database import get_db
from ..dao.group_dao import GroupDao
from ..models import User, UserGroup
from ..schemas import (
    AssignGroupPermissionsRequest,
    AssignMembersRequest,
    GroupCreateRequest,
    GroupUpdateRequest,
)
from ..services import group_service

router = APIRouter(prefix="/api/groups", tags=["分组管理"])


def _to_out(group: UserGroup) -> dict:
    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "member_count": len(group.users),
        "permission_ids": [p.id for p in group.permissions],
        "created_at": group.created_at.isoformat(),
    }


def _member_out(u: User) -> dict:
    return {"id": u.id, "username": u.username, "email": u.email, "status": u.status}


@router.get("")
def list_groups(_: User = Depends(require_permission("group:list")), db: Session = Depends(get_db)):
    return ok([_to_out(g) for g in GroupDao.list_all(db)])


@router.post("")
def create_group(
    req: GroupCreateRequest,
    request: Request,
    operator: User = Depends(require_permission("group:create")),
    db: Session = Depends(get_db),
):
    group = group_service.create_group(db, req.name, req.description, req.user_ids)
    record_log(db, "group.create", ip=client_ip(request), user_id=operator.id, username=operator.username,
               params={"name": req.name, "member_count": len(req.user_ids)})
    return ok(_to_out(group), message=f"分组创建成功，已加入 {len(req.user_ids)} 名用户")


@router.put("/{group_id}")
def update_group(
    group_id: int,
    req: GroupUpdateRequest,
    request: Request,
    operator: User = Depends(require_permission("group:edit")),
    db: Session = Depends(get_db),
):
    group = GroupDao.get_by_id(db, group_id)
    if group is None:
        raise BizError("分组不存在", status_code=404, code=4040)
    group_service.update_group(db, group, req.name, req.description)
    record_log(db, "group.edit", ip=client_ip(request), user_id=operator.id, username=operator.username,
               params={"group": group.name})
    return ok(_to_out(group))


@router.delete("/{group_id}")
def delete_group(
    group_id: int,
    request: Request,
    operator: User = Depends(require_permission("group:delete")),
    db: Session = Depends(get_db),
):
    group = GroupDao.get_by_id(db, group_id)
    if group is None:
        raise BizError("分组不存在", status_code=404, code=4040)
    group_service.delete_group(db, group)
    record_log(db, "group.delete", ip=client_ip(request), user_id=operator.id, username=operator.username,
               params={"group": group.name})
    return ok(message="分组已删除（成员与权限关系一并解除）")


@router.get("/{group_id}/members")
def list_members(
    group_id: int,
    _: User = Depends(require_permission("group:list")),
    db: Session = Depends(get_db),
):
    group = GroupDao.get_by_id(db, group_id)
    if group is None:
        raise BizError("分组不存在", status_code=404, code=4040)
    return ok([_member_out(u) for u in group.users])


@router.put("/{group_id}/members")
def assign_members(
    group_id: int,
    req: AssignMembersRequest,
    request: Request,
    operator: User = Depends(require_permission("group:assign_member")),
    db: Session = Depends(get_db),
):
    group = GroupDao.get_by_id(db, group_id)
    if group is None:
        raise BizError("分组不存在", status_code=404, code=4040)
    group_service.assign_members(db, group, req.user_ids)
    record_log(db, "group.assign_member", ip=client_ip(request), user_id=operator.id, username=operator.username,
               params={"group": group.name, "user_ids": req.user_ids})
    return ok(_to_out(group), message=f"已为分组分配 {len(req.user_ids)} 名用户")


@router.get("/{group_id}/permissions")
def get_group_permissions(
    group_id: int,
    _: User = Depends(require_permission("group:list")),
    db: Session = Depends(get_db),
):
    group = GroupDao.get_by_id(db, group_id)
    if group is None:
        raise BizError("分组不存在", status_code=404, code=4040)
    return ok([p.id for p in group.permissions])


@router.put("/{group_id}/permissions")
def assign_permissions(
    group_id: int,
    req: AssignGroupPermissionsRequest,
    request: Request,
    operator: User = Depends(require_permission("group:assign_permission")),
    db: Session = Depends(get_db),
):
    group = GroupDao.get_by_id(db, group_id)
    if group is None:
        raise BizError("分组不存在", status_code=404, code=4040)
    group_service.assign_permissions(db, group, req.permission_ids)
    record_log(db, "group.assign_permission", ip=client_ip(request), user_id=operator.id, username=operator.username,
               params={"group": group.name, "permission_ids": req.permission_ids})
    return ok(message="分组权限已统一更新")
