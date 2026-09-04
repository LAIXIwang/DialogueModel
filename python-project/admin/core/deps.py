"""依赖注入：数据库会话 / 当前用户 / RBAC 权限校验 / 客户端 IP。"""

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import jwt as pyjwt

from ..database import get_db
from ..models import User
from . import redis_client
from .exceptions import BizError
from .security import decode_token

_bearer = HTTPBearer(auto_error=False)


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db=Depends(get_db),
) -> User:
    """JWT 全局拦截：解析 → 黑名单校验 → 封禁校验 → 加载用户 → 状态校验。"""
    if credentials is None:
        raise BizError("未登录或令牌缺失", status_code=401, code=4010)
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except pyjwt.ExpiredSignatureError:
        raise BizError("令牌已过期，请重新登录", status_code=401, code=4011)
    except pyjwt.PyJWTError:
        raise BizError("令牌无效", status_code=401, code=4012)

    if payload.get("type") != "access":
        raise BizError("请使用访问令牌", status_code=401, code=4013)

    # 登出黑名单 / 禁用黑名单（JWT 主动失效的唯一手段）
    jti = payload.get("jti", "")
    if jti and redis_client.is_token_blacklisted(jti):
        raise BizError("令牌已登出失效", status_code=401, code=4014)
    if redis_client.is_user_banned(int(payload.get("sub", 0))):
        raise BizError("账号已被禁用", status_code=403, code=4031)

    user = db.get(User, int(payload.get("sub", 0)))
    if user is None:
        raise BizError("用户不存在", status_code=401, code=4015)
    if user.status != 1:
        raise BizError("账号已被禁用", status_code=403, code=4031)
    # 密码版本校验：改密/重置后旧令牌立即失效
    if int(payload.get("pwdv", 0)) != (user.pwd_version or 0):
        raise BizError("令牌已失效，请重新登录", status_code=401, code=4016)

    # 供审计与限流复用
    request.state.token_payload = payload
    request.state.user = user
    return user


def require_permission(perm_code: str):
    """RBAC 全局权限拦截器工厂：用法 Depends(require_permission('user:list'))。

    校验的用户权限 = 角色权限 ∪ 分组权限；超级管理员直接放行。
    """

    def checker(request: Request, user: User = Depends(get_current_user), db=Depends(get_db)) -> User:
        if user.role.code == "super_admin":
            return user
        from ..dao.rbac_dao import PermissionDao

        perms = PermissionDao.codes_by_user(user)
        if perm_code not in perms:
            raise BizError(f"无权限: {perm_code}", status_code=403, code=4030)
        return user

    return checker
