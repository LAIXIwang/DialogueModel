"""管理平台集中配置（可用 .env 覆盖）。"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class AdminSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ---- 服务 ----
    admin_host: str = "127.0.0.1"
    admin_port: int = 8001
    admin_env: str = "dev"

    # ---- MySQL ----
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = "123456"
    mysql_db: str = "DialogueModel"

    # ---- Redis ----
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_db: int = 0

    # ---- JWT ----
    jwt_secret: str = "dialogue-admin-jwt-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 120
    refresh_token_expire_days: int = 7

    # ---- 配额与限流 ----
    rate_limit_per_minute: int = 10  # 单用户每分钟最多 AI 请求次数（Redis 存储，运行时可改）
    default_daily_quota: int = 100_000  # 新用户默认每日 token 上限

    # ---- 模型接入默认值（与 .env 的 UPSTREAM_* 一致；管理平台可实时覆盖）----
    upstream_base_url: str = "http://127.0.0.1:9190/v1"
    upstream_api_key: str = ""
    upstream_protocol: str = "openai"
    upstream_model: str = "dialogue-model"

    # ---- 邮件（找回密码验证码）----
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_ssl: bool = True  # 465 端口用 SSL；587 端口设 False 并开启 STARTTLS
    smtp_starttls: bool = False

    # ---- CORS ----
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def sqlalchemy_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}?charset=utf8mb4"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_admin_settings() -> AdminSettings:
    return AdminSettings()
