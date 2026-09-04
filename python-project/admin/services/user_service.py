"""用户管理服务：CRUD、启用/禁用、重置密码、分配角色、个人资料。"""

from sqlalchemy.orm import Session

from ..config import get_admin_settings
from ..core import redis_client
from ..core.exceptions import BizError
from ..core.security import hash_password
from ..dao.business_dao import QuotaDao
from ..dao.rbac_dao import RoleDao
from ..dao.user_dao import UserDao
from ..models import User

# 管理员可管理的角色范围：普通用户 + 访客
ADMIN_MANAGEABLE_ROLES = ("user", "guest")


def ensure_can_manage(operator: User, target: User) -> None:
    """管理范围校验：
    超级管理员可管理所有角色；管理员仅能管理普通用户与访客（不能动超级管理员/其他管理员）。
    """
    if operator.role.code == "super_admin":
        return
    if target.role.code not in ADMIN_MANAGEABLE_ROLES:
        raise BizError("管理员仅能管理普通用户与访客账号", status_code=403, code=4030)


def create_user(db: Session, operator: User, username: str, password: str, role_id: int, phone: str, email: str) -> User:
    if UserDao.get_by_username(db, username) is not None:
        raise BizError("用户名已存在", code=4001)
    role = RoleDao.get_by_id(db, role_id)
    if role is None:
        raise BizError("角色不存在", code=4003)
    # 管理员新建用户时只能授予普通用户/访客角色
    if operator.role.code != "super_admin" and role.code not in ADMIN_MANAGEABLE_ROLES:
        raise BizError("管理员仅能为新用户分配普通用户或访客角色", status_code=403, code=4030)
    user = UserDao.create(db, username, hash_password(password), role_id, phone, email)
    QuotaDao.get_or_create(db, user.id, get_admin_settings().default_daily_quota)
    return user


def set_status(db: Session, operator: User, target: User, status: int) -> None:
    ensure_can_manage(operator, target)
    if target.id == operator.id and status == 0:
        raise BizError("不能禁用自己", code=4004)
    UserDao.update_status(db, target, status)
    if status == 0:
        # 禁用 = 入黑名单：封禁其在线令牌
        redis_client.ban_user(target.id, get_admin_settings().refresh_token_expire_days * 86400)
        redis_client.delete_session_cache(target.id)
    else:
        redis_client.unban_user(target.id)


def reset_password(db: Session, operator: User, target: User, new_password: str) -> None:
    ensure_can_manage(operator, target)
    UserDao.update_password(db, target, hash_password(new_password))
    # 密码版本已 +1：该用户旧令牌全部失效
    redis_client.delete_session_cache(target.id)


def assign_role(db: Session, operator: User, target: User, role_id: int) -> None:
    ensure_can_manage(operator, target)
    if RoleDao.get_by_id(db, role_id) is None:
        raise BizError("角色不存在", code=4003)
    UserDao.assign_role(db, target, role_id)
    redis_client.delete_session_cache(target.id)


def delete_user(db: Session, operator: User, target: User) -> None:
    if target.role.code == "super_admin":
        raise BizError("超级管理员不可删除", code=4005)
    if target.id == operator.id:
        raise BizError("不能删除自己", code=4006)
    ensure_can_manage(operator, target)
    db.delete(target)
    db.commit()
    redis_client.delete_session_cache(target.id)
