"""Pydantic 请求/响应契约。"""

from datetime import datetime

from pydantic import BaseModel, Field


# ------------------------------ 通用分页 ------------------------------
class PageResult(BaseModel):
    total: int
    items: list


# ------------------------------ 认证 ------------------------------
class LoginRequest(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=2, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)
    email: str = Field(default="", max_length=128)


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # 秒


class RefreshRequest(BaseModel):
    refresh_token: str


class UserBrief(BaseModel):
    id: int
    username: str
    email: str = ""
    phone: str = ""
    avatar: str = ""
    role_code: str = ""
    role_name: str = ""
    status: int = 1
    permissions: list[str] = []


# ------------------------------ 用户管理 ------------------------------
class UserCreateRequest(BaseModel):
    username: str = Field(min_length=2, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)
    phone: str = Field(default="", max_length=32)
    email: str = Field(default="", max_length=128)
    role_id: int


class UserUpdateRequest(BaseModel):
    phone: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=128)
    avatar: str | None = Field(default=None, max_length=512)


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)


class StatusRequest(BaseModel):
    status: int = Field(ge=0, le=1)  # 1 启用 / 0 禁用


class AssignRoleRequest(BaseModel):
    role_id: int


class UserOut(BaseModel):
    id: int
    username: str
    phone: str
    email: str
    avatar: str
    role_id: int
    role_code: str
    role_name: str
    status: int
    groups: list[str] = []
    created_at: datetime
    last_login_at: datetime | None


# ------------------------------ 角色 / 权限 ------------------------------
class RoleCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=32, pattern=r"^[a-z0-9_]+$")
    name: str = Field(min_length=1, max_length=64)
    description: str = Field(default="", max_length=255)


class RoleUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=255)


class AssignPermissionsRequest(BaseModel):
    permission_ids: list[int]


class RoleOut(BaseModel):
    id: int
    code: str
    name: str
    description: str
    user_count: int = 0
    permission_ids: list[int] = []


class PermissionOut(BaseModel):
    id: int
    code: str
    name: str
    module: str


# ------------------------------ 分组管理 ------------------------------
class GroupCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    description: str = Field(default="", max_length=255)
    user_ids: list[int] = Field(default=[], max_length=500)  # 建组时同步勾选的用户


class GroupUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=255)


class AssignMembersRequest(BaseModel):
    user_ids: list[int] = Field(min_length=1, max_length=500)


class AssignGroupPermissionsRequest(BaseModel):
    permission_ids: list[int] = Field(default=[], max_length=200)


class GroupOut(BaseModel):
    id: int
    name: str
    description: str
    member_count: int = 0
    permission_ids: list[int] = []
    created_at: datetime


# ------------------------------ 模型接入 ------------------------------
class UpdateModelConfigRequest(BaseModel):
    base_url: str | None = Field(default=None, max_length=512)
    api_key: str | None = Field(default=None, max_length=512)  # 留空 = 保留原密钥
    protocol: str | None = Field(default=None, pattern=r"^(openai|llamacpp)$")
    model: str | None = Field(default=None, max_length=128)


class ModelConfigOut(BaseModel):
    base_url: str
    api_key: str
    protocol: str
    model: str
    updated_by: str = ""
    updated_at: str = ""


# ------------------------------ 会话 / 对话 ------------------------------
class ConversationOut(BaseModel):
    id: int
    user_id: int | None
    username: str
    model: str
    prompt: str
    answer: str
    tokens: int
    session_id: str
    ip: str
    created_at: datetime


# ------------------------------ 配额 / 统计 ------------------------------
class QuotaOut(BaseModel):
    user_id: int
    username: str
    daily_limit: int
    used_today: int
    used_total: int
    remaining: int
    last_date: str


class UpdateQuotaRequest(BaseModel):
    daily_limit: int = Field(ge=0, le=10_000_000_000)


class RateLimitOut(BaseModel):
    per_minute: int


class UpdateRateLimitRequest(BaseModel):
    per_minute: int = Field(ge=1, le=10000)


class StatsOverview(BaseModel):
    total_users: int
    enabled_users: int
    disabled_users: int
    today_calls: int
    today_tokens: int
    total_calls: int
    total_tokens: int
    online_sessions: int
    rate_limit_per_minute: int


# ------------------------------ 审计日志 ------------------------------
class LogOut(BaseModel):
    id: int
    user_id: int | None
    username: str
    action: str
    ip: str
    params: str
    detail: str
    created_at: datetime
