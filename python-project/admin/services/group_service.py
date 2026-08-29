"""分组服务：自定义命名分组、多选用户统一入组、分组级权限统一分配。"""

from sqlalchemy.orm import Session

from ..core.exceptions import BizError
from ..dao.group_dao import GroupDao
from ..dao.rbac_dao import PermissionDao
from ..dao.user_dao import UserDao
from ..models import UserGroup


def create_group(db: Session, name: str, description: str, user_ids: list[int] | None = None) -> UserGroup:
    """创建分组，可同时把勾选的多个用户统一入组。"""
    if GroupDao.get_by_name(db, name) is not None:
        raise BizError("分组名称已存在", code=4201)
    group = GroupDao.create(db, name, description)
    if user_ids:
        assign_members(db, group, user_ids)
    return group


def update_group(db: Session, group: UserGroup, name: str | None, description: str | None) -> None:
    if name is not None and name != group.name and GroupDao.get_by_name(db, name) is not None:
        raise BizError("分组名称已存在", code=4201)
    GroupDao.update(db, group, name, description)


def delete_group(db: Session, group: UserGroup) -> None:
    GroupDao.delete(db, group)


def assign_members(db: Session, group: UserGroup, user_ids: list[int]) -> None:
    """把多个用户统一纳入分组（整体替换）。"""
    users = UserDao.get_by_ids(db, user_ids)
    if len(users) != len(set(user_ids)):
        raise BizError("存在无效的用户 ID", code=4202)
    GroupDao.set_members(db, group, user_ids)


def assign_permissions(db: Session, group: UserGroup, permission_ids: list[int]) -> None:
    """给分组统一分配权限，组内所有用户共享。"""
    valid = PermissionDao.get_by_ids(db, permission_ids)
    if len(valid) != len(set(permission_ids)):
        raise BizError("存在无效的权限 ID", code=4203)
    GroupDao.set_permissions(db, group, permission_ids)
