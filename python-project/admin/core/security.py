"""密码加密（bcrypt）与 JWT 签发/解析。"""

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from ..config import get_admin_settings


# ------------------------------ 密码 ------------------------------
def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


# ------------------------------ JWT ------------------------------
def _create_token(user_id: int, username: str, role_code: str, token_type: str, expires_delta: timedelta) -> tuple[str, str]:
    settings = get_admin_settings()
    now = datetime.now(timezone.utc)
    jti = uuid.uuid4().hex
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role_code,
        "type": token_type,  # access | refresh
        "jti": jti,
        "iat": now,
        "exp": now + expires_delta,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, jti


def create_access_token(user_id: int, username: str, role_code: str) -> tuple[str, str]:
    settings = get_admin_settings()
    return _create_token(
        user_id, username, role_code, "access",
        timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(user_id: int, username: str, role_code: str) -> tuple[str, str]:
    settings = get_admin_settings()
    return _create_token(
        user_id, username, role_code, "refresh",
        timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(token: str) -> dict:
    """解析并校验 JWT，失败抛 jwt.PyJWTError。"""
    settings = get_admin_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def token_expire_seconds(payload: dict) -> int:
    exp = payload.get("exp")
    if not exp:
        return 0
    return max(0, int(exp - datetime.now(timezone.utc).timestamp()))
