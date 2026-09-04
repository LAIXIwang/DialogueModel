"""用户表：账号、密码(bcrypt 密文)、联系方式、角色、状态、时间戳。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)  # bcrypt 密文，绝不存明文
    phone: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    email: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    avatar: Mapped[str] = mapped_column(String(512), default="", nullable=False)  # 对象存储 URL
    role_id: Mapped[int] = mapped_column(ForeignKey("role.id"), nullable=False, index=True)
    status: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 1 启用 / 0 禁用
    pwd_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 密码版本：改密后 +1，旧令牌全部失效
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    role: Mapped["Role"] = relationship(back_populates="users", lazy="joined")
    groups: Mapped[list["UserGroup"]] = relationship(  # noqa: F821
        secondary="user_group_member", back_populates="users", lazy="selectin"
    )
