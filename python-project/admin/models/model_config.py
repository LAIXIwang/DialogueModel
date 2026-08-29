"""模型接入配置表（单行）：本地/自建大模型 API 的连接参数。"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class ModelConfig(Base):
    __tablename__ = "model_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    base_url: Mapped[str] = mapped_column(String(512), nullable=False)  # 接口地址
    api_key: Mapped[str] = mapped_column(String(512), default="", nullable=False)  # 密钥（服务端持有）
    protocol: Mapped[str] = mapped_column(String(32), default="openai", nullable=False)  # openai | llamacpp
    model: Mapped[str] = mapped_column(String(128), default="", nullable=False)  # 模型名称
    updated_by: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
