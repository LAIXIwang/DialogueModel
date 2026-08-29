"""RBAC：角色表、权限表、角色-权限多对多中间表。"""

from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

# 角色-权限中间表（多对多）
role_permission = Table(
    "role_permission",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("role.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permission.id", ondelete="CASCADE"), primary_key=True),
)


class Role(Base):
    __tablename__ = "role"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)  # super_admin/admin/user/guest
    name: Mapped[str] = mapped_column(String(64), nullable=False)  # 超级管理员/管理员/普通用户/访客
    description: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="role")  # noqa: F821
    permissions: Mapped[list["Permission"]] = relationship(
        secondary=role_permission, lazy="selectin"
    )


class Permission(Base):
    __tablename__ = "permission"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)  # user:list、conversation:read、rag:upload…
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    module: Mapped[str] = mapped_column(String(64), default="", nullable=False)  # 所属模块

    roles: Mapped[list["Role"]] = relationship(secondary=role_permission, back_populates="permissions")
