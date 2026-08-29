"""用户分组：分组表 + 分组-用户多对多 + 分组-权限多对多。

用户最终权限 = 角色权限 ∪ 所有分组权限。
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

# 分组-用户中间表（多对多）
user_group_member = Table(
    "user_group_member",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("user.id", ondelete="CASCADE"), primary_key=True),
    Column("group_id", Integer, ForeignKey("user_group.id", ondelete="CASCADE"), primary_key=True),
)

# 分组-权限中间表（多对多）
group_permission = Table(
    "group_permission",
    Base.metadata,
    Column("group_id", Integer, ForeignKey("user_group.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permission.id", ondelete="CASCADE"), primary_key=True),
)


class UserGroup(Base):
    __tablename__ = "user_group"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    users: Mapped[list["User"]] = relationship(  # noqa: F821
        secondary=user_group_member, back_populates="groups", lazy="selectin"
    )
    permissions: Mapped[list["Permission"]] = relationship(  # noqa: F821
        secondary=group_permission, lazy="selectin"
    )
