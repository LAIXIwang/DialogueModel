"""Redis 公共封装：token 黑名单 / 用户封禁 / 会话缓存 / 用户限流 / 运行配置。

Redis 5.0（Windows 版）完全支持以下全部命令。
"""

import time

import redis

from ..config import get_admin_settings

_settings = get_admin_settings()

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    """惰性单例连接（进程内共享连接池）。"""
    global _client
    if _client is None:
        _client = redis.Redis(
            host=_settings.redis_host,
            port=_settings.redis_port,
            db=_settings.redis_db,
            decode_responses=True,
            socket_connect_timeout=3,
            protocol=2,  # RESP2：兼容 Redis 5.x（Windows 版无 HELLO 命令）
        )
        _client.ping()
    return _client


# ------------------------------ Token 黑名单 ------------------------------
def blacklist_token(jti: str, expire_seconds: int) -> None:
    """登出时把 token 的 jti 拉黑至其自然过期。"""
    if expire_seconds > 0:
        get_redis().setex(f"auth:bl:{jti}", expire_seconds, "1")


def is_token_blacklisted(jti: str) -> bool:
    return bool(get_redis().exists(f"auth:bl:{jti}"))


# ------------------------------ 用户封禁（黑名单） ------------------------------
def ban_user(user_id: int, seconds: int) -> None:
    """禁用用户时封禁其所有在线令牌（依赖 get_current_user 校验）。"""
    if seconds > 0:
        get_redis().setex(f"auth:ban:{user_id}", seconds, "1")


def unban_user(user_id: int) -> None:
    get_redis().delete(f"auth:ban:{user_id}")


def is_user_banned(user_id: int) -> bool:
    return bool(get_redis().exists(f"auth:ban:{user_id}"))


# ------------------------------ 会话缓存 ------------------------------
def cache_session(user_id: int, data: dict, expire_seconds: int = 3600) -> None:
    get_redis().setex(f"auth:sess:{user_id}", expire_seconds, __import__("json").dumps(data, ensure_ascii=False))


def get_cached_session(user_id: int) -> dict | None:
    raw = get_redis().get(f"auth:sess:{user_id}")
    if raw is None:
        return None
    import json

    try:
        return json.loads(raw)
    except ValueError:
        return None


def delete_session_cache(user_id: int) -> None:
    get_redis().delete(f"auth:sess:{user_id}")


# ------------------------------ 用户限流（滑动窗口：每分钟 N 次） ------------------------------
def rate_limit_check(user_id: int, max_per_minute: int | None = None) -> tuple[bool, int]:
    """返回 (是否放行, 剩余可调用次数)。每分钟窗口，固定窗口实现（Redis INCR+EXPIRE）。"""
    r = get_redis()
    if max_per_minute is None:
        max_per_minute = int(r.get("config:rate_limit") or _settings.rate_limit_per_minute)
    key = f"ratelimit:user:{user_id}:{int(time.time() // 60)}"
    current = r.incr(key)
    if current == 1:
        r.expire(key, 120)
    remaining = max(0, max_per_minute - current)
    return current <= max_per_minute, remaining


# ------------------------------ 运行时可调配置 ------------------------------
def get_rate_limit_config() -> int:
    return int(get_redis().get("config:rate_limit") or _settings.rate_limit_per_minute)


def set_rate_limit_config(per_minute: int) -> None:
    get_redis().set("config:rate_limit", per_minute)


# ------------------------------ 找回密码：邮箱验证码 ------------------------------
CODE_TTL = 600          # 验证码 10 分钟有效
CODE_MAX_ATTEMPTS = 5   # 最多输错 5 次
SEND_WINDOW = 900       # 发送限流窗口 15 分钟
SEND_MAX = 5            # 窗口内最多发送 5 次
RESET_TOKEN_TTL = 600   # 重置令牌 10 分钟有效（一次性）


def set_reset_code(user_id: int, code: str) -> None:
    r = get_redis()
    r.setex(f"reset:code:{user_id}", CODE_TTL, code)
    r.delete(f"reset:attempts:{user_id}")


def check_reset_code(user_id: int, code: str) -> bool:
    """校验验证码；输错计数，超过上限即作废。"""
    r = get_redis()
    stored = r.get(f"reset:code:{user_id}")
    if stored is None:
        return False
    if stored != code:
        attempts = r.incr(f"reset:attempts:{user_id}")
        r.expire(f"reset:attempts:{user_id}", CODE_TTL)
        if attempts >= CODE_MAX_ATTEMPTS:
            r.delete(f"reset:code:{user_id}")
        return False
    return True


def clear_reset_code(user_id: int) -> None:
    r = get_redis()
    r.delete(f"reset:code:{user_id}", f"reset:attempts:{user_id}")


def send_rate_ok(user_id: int) -> bool:
    """发送限流：15 分钟内最多 5 次。"""
    r = get_redis()
    key = f"reset:send:{user_id}:{int(time.time() // SEND_WINDOW)}"
    n = r.incr(key)
    if n == 1:
        r.expire(key, SEND_WINDOW * 2)
    return n <= SEND_MAX


def issue_reset_token(user_id: int) -> str:
    import uuid

    token = uuid.uuid4().hex
    get_redis().setex(f"reset:token:{token}", RESET_TOKEN_TTL, str(user_id))
    return token


def consume_reset_token(token: str) -> int | None:
    """一次性重置令牌：取出即作废。"""
    r = get_redis()
    key = f"reset:token:{token}"
    uid = r.get(key)
    if uid is None:
        return None
    r.delete(key)
    return int(uid)
