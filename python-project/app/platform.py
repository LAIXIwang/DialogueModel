"""BFF ↔ 用户管理平台集成。

当浏览器携带平台 JWT（Authorization: Bearer <access_token>）请求 /api/v1/chat 时：
  1. JWT 校验（黑名单 / 封禁 / 状态）
  2. Redis 用户限流（单用户每分钟 N 次）
  3. MySQL 配额判断（每日 token 上限）
  4. 生成结束后：对话记录入库 + 配额扣减 + AI 调用审计

未携带 JWT 时回退到 CLIENT_API_KEYS 模式（保持原有开发调试能力）。
"""

import asyncio
import os
import sys
from datetime import date

from fastapi import HTTPException

# 保证可导入 admin 包（uvicorn 从 python-project 启动）
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import jwt as pyjwt  # noqa: E402

from admin.core import redis_client  # noqa: E402
from admin.core.audit import record_log  # noqa: E402
from admin.core.security import decode_token  # noqa: E402
from admin.dao.business_dao import ConversationDao, QuotaDao  # noqa: E402
from admin.dao.user_dao import UserDao  # noqa: E402
from admin.database import SessionLocal  # noqa: E402
from admin.models import User  # noqa: E402


def looks_like_jwt(token: str) -> bool:
    return token.count(".") == 2


async def platform_auth(token: str) -> User | None:
    """校验平台 JWT，返回用户对象；非法令牌直接抛 401/403。"""
    try:
        payload = decode_token(token)
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(401, "平台令牌已过期，请重新登录")
    except pyjwt.PyJWTError:
        raise HTTPException(401, "平台令牌无效")

    if payload.get("type") != "access":
        raise HTTPException(401, "请使用访问令牌")

    jti = payload.get("jti", "")
    if jti and redis_client.is_token_blacklisted(jti):
        raise HTTPException(401, "令牌已登出失效")

    user_id = int(payload.get("sub", 0))
    if redis_client.is_user_banned(user_id):
        raise HTTPException(403, "账号已被禁用")

    db = SessionLocal()
    try:
        user = UserDao.get_by_id(db, user_id)
    finally:
        db.close()
    if user is None:
        raise HTTPException(401, "用户不存在")
    if user.status != 1:
        raise HTTPException(403, "账号已被禁用")
    # 密码版本校验：改密/重置后旧令牌立即失效
    if int(payload.get("pwdv", 0)) != (user.pwd_version or 0):
        raise HTTPException(401, "令牌已失效，请重新登录")
    return user


async def enforce_limits(user_id: int) -> None:
    """调用前：Redis 速率限制 + 每日配额判断。"""
    allowed, remaining = redis_client.rate_limit_check(user_id)
    if not allowed:
        limit = redis_client.get_rate_limit_config()
        raise HTTPException(
            429,
            f"请求过于频繁：单用户每分钟最多 {limit} 次 AI 请求",
            headers={"Retry-After": "60"},
        )

    def _check_quota() -> None:
        db = SessionLocal()
        try:
            quota = QuotaDao.get_or_create(db, user_id, 100_000)
            today = date.today().isoformat()
            used_today = quota.used_today if quota.last_date == today else 0
            if used_today >= quota.daily_limit:
                raise HTTPException(429, "今日 AI 配额已用尽，请联系管理员")
        finally:
            db.close()

    await asyncio.to_thread(_check_quota)


def record_chat(
    *,
    user: User,
    model: str,
    prompt: str,
    answer: str,
    tokens: int,
    session_id: str,
    ip: str,
) -> None:
    """调用后：对话入库 + 配额扣减 + AI 调用审计。"""
    db = SessionLocal()
    try:
        ConversationDao.create(
            db,
            user_id=user.id,
            username=user.username,
            model=model,
            prompt=prompt,
            answer=answer,
            tokens=tokens,
            session_id=session_id,
            ip=ip,
        )
        quota = QuotaDao.get_or_create(db, user.id, 100_000)
        QuotaDao.deduct(db, quota, tokens)
        record_log(
            db,
            "ai.call",
            ip=ip,
            user_id=user.id,
            username=user.username,
            params={"model": model, "tokens": tokens, "session_id": session_id},
        )
    finally:
        db.close()
