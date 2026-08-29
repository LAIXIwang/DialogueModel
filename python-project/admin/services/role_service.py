"""角色与权限服务：角色维护 + 给角色分配权限 + 给用户分配角色。"""

from sqlalchemy.orm import Session

from ..core.exceptions import BizError
from ..dao.rbac_dao import PermissionDao, RoleDao
from ..models import Role


def create_role(db: Session, code: str, name: str, description: str) -> Role:
    if RoleDao.get_by_code(db, code) is not None:
        raise BizError("角色编码已存在", code=4101)
    return RoleDao.create(db, code, name, description)


def update_role(db: Session, role: Role, name: str | None, description: str | None) -> None:
    RoleDao.update(db, role, name, description)


def delete_role(db: Session, role: Role) -> None:
    if role.code in ("super_admin", "admin", "user", "guest"):
        raise BizError("内置角色不可删除", code=4102)
    if RoleDao.user_count(db, role.id) > 0:
        raise BizError("该角色下仍有用户，无法删除", code=4103)
    RoleDao.delete(db, role)


def assign_permissions(db: Session, role: Role, permission_ids: list[int]) -> None:
    if role.code == "super_admin":
        raise BizError("超级管理员默认拥有全部权限，无需分配", code=4104)
    valid = PermissionDao.get_by_ids(db, permission_ids)
    if len(valid) != len(set(permission_ids)):
        raise BizError("存在无效的权限 ID", code=4105)
    RoleDao.set_permissions(db, role, valid)
