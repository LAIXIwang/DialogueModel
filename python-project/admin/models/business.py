"""业务表：对话记录 / 用户配额 / 操作审计日志。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Conversation(Base):
    """AI 对话记录表（由 BFF 在每次模型调用后写入）。"""

    __tablename__ = "conversation"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id", ondelete="SET NULL"), nullable=True, index=True)
    username: Mapped[str] = mapped_column(String(64), default="", nullable=False)  # 冗余，便于审计展示
    model: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)  # 提问
    answer: Mapped[str] = mapped_column(Text, nullable=False)  # 回答
    tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 本次消耗 token
    session_id: Mapped[str] = mapped_column(String(64), default="", nullable=False, index=True)
    ip: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False, index=True)


class ApiQuota(Base):
    """用户配额表：每日 token 上限 + 累计消耗 + 剩余额度。"""

    __tablename__ = "api_quota"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    daily_limit: Mapped[int] = mapped_column(Integer, default=100_000, nullable=False)  # 每日 token 上限
    used_today: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 今日已消耗
    used_total: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)  # 累计消耗
    last_date: Mapped[str] = mapped_column(String(16), default="", nullable=False)  # 用于跨天重置
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    @property
    def remaining(self) -> int:
        return max(0, self.daily_limit - self.used_today)


class OperateLog(Base):
    """操作审计日志：登录 / 后台操作 / AI 调用，IP 溯源。"""

    __tablename__ = "operate_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id", ondelete="SET NULL"), nullable=True, index=True)
    username: Mapped[str] = mapped_column(String(64), default="", nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # login/user.create/ai.call/...
    ip: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    params: Mapped[str] = mapped_column(Text, nullable=False)  # 请求参数（脱敏后）
    detail: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False, index=True)
