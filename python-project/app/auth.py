"""鉴权：校验浏览器端 Bearer 令牌。

令牌只保护「浏览器 → BFF」这一段；上游模型 API 的密钥由服务端持有，
绝不透传给浏览器。
"""

import hmac

from fastapi import Header, HTTPException

from .config import get_settings


async def require_auth(
    authorization: str | None = Header(default=None),
) -> None:
    settings = get_settings()
    keys = settings.allowed_keys

    if not keys:
        # 未配置任何客户端密钥：仅允许开发环境放行，生产环境直接拒绝
        if settings.app_env != "dev":
            raise HTTPException(status_code=503, detail="服务端未配置客户端密钥（CLIENT_API_KEYS）")
        return

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401,
            detail="缺少认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization[7:].strip()
    if not any(hmac.compare_digest(token, key) for key in keys):
        raise HTTPException(status_code=401, detail="认证令牌无效")
