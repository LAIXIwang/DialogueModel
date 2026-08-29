"""请求 / 响应数据模型。"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=200_000)


class ChatRequest(BaseModel):
    """浏览器 → BFF 的聊天请求（OpenAI 风格）。"""

    messages: list[ChatMessage] = Field(min_length=1, max_length=64)
    model: Optional[str] = None  # 留空使用 BFF 默认模型
    temperature: Optional[float] = Field(default=None, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=None, ge=1, le=131_072)
    stream: bool = True  # BFF 对浏览器统一使用 SSE，此字段保留以兼容协议


class SessionInfo(BaseModel):
    id: str
    title: str
    message_count: int
    created_at: float
    updated_at: float


class SessionDetail(SessionInfo):
    messages: list[ChatMessage]
