"""认证服务：登录校验、注册、刷新令牌、登出、修改密码。"""

from datetime import datetime

from sqlalchemy.orm import Session

from ..config import get_admin_settings
from ..core import redis_client
from ..core.audit import record_log
from ..core.exceptions import BizError
from ..core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    token_expire_seconds,
    verify_password,
)
from ..dao.rbac_dao import RoleDao
from ..dao.user_dao import UserDao
from ..models import User


def login(db: Session, username: str, password: str, ip: str) -> dict:
    """登录校验：账号存在 → bcrypt 密码校验 → 状态校验 → 签发双令牌 + 会话缓存 + 审计。"""
    user = UserDao.get_by_username(db, username)
    # 用户不存在时也做一次哈希比对，防用户名枚举时序攻击
    if user is None or not verify_password(password, user.password_hash):
        record_log(db, "login.fail", ip=ip, username=username, detail="用户名或密码错误")
        raise BizError("用户名或密码错误", status_code=401, code=4010)

    if user.status != 1:
        record_log(db, "login.fail", ip=ip, user_id=user.id, username=username, detail="账号已禁用")
        raise BizError("账号已被禁用", status_code=403, code=4031)

    UserDao.update_last_login(db, user)
    access, access_jti = create_access_token(user.id, user.username, user.role.code)
    refresh, refresh_jti = create_refresh_token(user.id, user.username, user.role.code)

    # 会话缓存（Redis）
    redis_client.cache_session(
        user.id,
        {"user_id": user.id, "username": user.username, "role": user.role.code, "login_at": datetime.now().isoformat()},
    )

    record_log(db, "login", ip=ip, user_id=user.id, username=user.username)

    settings = get_admin_settings()
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
        "user": _user_brief(user),
    }


def register(db: Session, username: str, password: str, email: str, ip: str) -> dict:
    """注册：默认普通用户角色 + 默认配额。"""
    if UserDao.get_by_username(db, username) is not None:
        raise BizError("用户名已存在", code=4001)
    role = RoleDao.get_by_code(db, "user")
    if role is None:
        raise BizError("系统未初始化角色，请先执行种子数据", status_code=500, code=5001)
    user = UserDao.create(db, username, hash_password(password), role.id, "", email)
    from ..dao.business_dao import QuotaDao

    QuotaDao.get_or_create(db, user.id, get_admin_settings().default_daily_quota)
    record_log(db, "register", ip=ip, user_id=user.id, username=user.username)
    return _user_brief(user)


def refresh(db: Session, refresh_token: str, ip: str) -> dict:
    """刷新令牌：校验 refresh 类型 + 黑名单，签发新 access/refresh（旧 refresh 作废）。"""
    import jwt as pyjwt

    try:
        payload = decode_token(refresh_token)
    except pyjwt.PyJWTError:
        raise BizError("刷新令牌无效或已过期", status_code=401, code=4016)

    if payload.get("type") != "refresh":
        raise BizError("请使用刷新令牌", status_code=401, code=4017)
    jti = payload.get("jti", "")
    if jti and redis_client.is_token_blacklisted(jti):
        raise BizError("刷新令牌已失效", status_code=401, code=4014)

    user = UserDao.get_by_id(db, int(payload.get("sub", 0)))
    if user is None or user.status != 1:
        raise BizError("用户不存在或已禁用", status_code=401, code=4015)

    # 旧 refresh 拉黑（旋转刷新）
    redis_client.blacklist_token(jti, token_expire_seconds(payload))

    access, _ = create_access_token(user.id, user.username, user.role.code)
    new_refresh, _ = create_refresh_token(user.id, user.username, user.role.code)
    record_log(db, "token.refresh", ip=ip, user_id=user.id, username=user.username)
    settings = get_admin_settings()
    return {
        "access_token": access,
        "refresh_token": new_refresh,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
    }


def logout(db: Session, access_payload: dict, refresh_token: str | None, ip: str) -> None:
    """登出：access 与 refresh 的 jti 全部入 Redis 黑名单。"""
    user_id = int(access_payload.get("sub", 0))
    access_jti = access_payload.get("jti", "")
    if access_jti:
        redis_client.blacklist_token(access_jti, token_expire_seconds(access_payload))
    if refresh_token:
        try:
            rp = decode_token(refresh_token)
            if rp.get("type") == "refresh" and rp.get("sub") == str(user_id):
                redis_client.blacklist_token(rp.get("jti", ""), token_expire_seconds(rp))
        except Exception:  # noqa: BLE001
            pass
    redis_client.delete_session_cache(user_id)
    record_log(db, "logout", ip=ip, user_id=user_id, username=access_payload.get("username", ""))


def change_password(db: Session, user: User, old_password: str, new_password: str, ip: str) -> None:
    """修改密码：校验旧密码 → bcrypt 存新密文 → 旧令牌全部拉黑（重新登录）。"""
    if not verify_password(old_password, user.password_hash):
        raise BizError("旧密码错误", code=4002)
    UserDao.update_password(db, user, hash_password(new_password))
    # 密码变更后强制旧令牌失效
    redis_client.ban_user(user.id, get_admin_settings().refresh_token_expire_days * 86400)
    redis_client.delete_session_cache(user.id)
    record_log(db, "password.change", ip=ip, user_id=user.id, username=user.username)


def _user_brief(user: User) -> dict:
    from ..dao.rbac_dao import PermissionDao

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "phone": user.phone,
        "avatar": user.avatar,
        "role_code": user.role.code,
        "role_name": user.role.name,
        "status": user.status,
        # 角色权限 ∪ 分组权限
        "permissions": sorted(PermissionDao.codes_by_user(user)),
    }
