"""集中配置：所有运行参数均可用环境变量 / .env 覆盖。"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- 服务 ----
    app_name: str = "Dialogue BFF"
    app_env: str = "dev"  # dev | prod
    host: str = "127.0.0.1"
    port: int = 8000

    # ---- 鉴权：允许的浏览器端客户端令牌（逗号分隔；留空 = 仅平台 JWT 鉴权）----
    client_api_keys: str = ""

    # ---- 上游自建模型 API ----
    upstream_base_url: str = "http://127.0.0.1:9190/v1"
    upstream_api_key: str = ""
    upstream_protocol: str = "openai"  # openai | llamacpp
    upstream_model: str = "dialogue-model"

    # 上游请求超时（秒）：read 需足够长以支持长时间流式生成
    connect_timeout: float = 10.0
    read_timeout: float = 300.0
    write_timeout: float = 30.0

    # ---- 限流 ----
    rate_limit_ip_per_minute: int = 30
    rate_limit_session_per_minute: int = 15

    # ---- 会话 ----
    session_ttl_minutes: int = 1440  # 24 小时
    max_history_messages: int = 40  # 带入模型的上下文消息条数上限

    # ---- SSE ----
    keepalive_seconds: float = 15.0  # 上游静默时的保活间隔

    # ---- CORS / 代理 ----
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    trust_proxy_headers: bool = True  # 经 Nginx 等反向代理时取 X-Forwarded-For

    @property
    def allowed_keys(self) -> set[str]:
        return {k.strip() for k in self.client_api_keys.split(",") if k.strip()}

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
