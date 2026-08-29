"""DAO：角色 / 权限。"""

from sqlalchemy.orm import Session

from ..models import Permission, Role, User


class RoleDao:
    @staticmethod
    def get_by_id(db: Session, role_id: int) -> Role | None:
        return db.get(Role, role_id)

    @staticmethod
    def get_by_code(db: Session, code: str) -> Role | None:
        return db.query(Role).filter(Role.code == code).first()

    @staticmethod
    def list_all(db: Session) -> list[Role]:
        return db.query(Role).order_by(Role.id.asc()).all()

    @staticmethod
    def create(db: Session, code: str, name: str, description: str) -> Role:
        role = Role(code=code, name=name, description=description)
        db.add(role)
        db.commit()
        db.refresh(role)
        return role

    @staticmethod
    def update(db: Session, role: Role, name: str | None, description: str | None) -> None:
        if name is not None:
            role.name = name
        if description is not None:
            role.description = description
        db.commit()

    @staticmethod
    def delete(db: Session, role: Role) -> None:
        db.delete(role)
        db.commit()

    @staticmethod
    def user_count(db: Session, role_id: int) -> int:
        return db.query(User).filter(User.role_id == role_id).count()

    @staticmethod
    def set_permissions(db: Session, role: Role, permission_ids: list[int]) -> None:
        role.permissions = db.query(Permission).filter(Permission.id.in_(permission_ids)).all()
        db.commit()


class PermissionDao:
    @staticmethod
    def list_all(db: Session) -> list[Permission]:
        return db.query(Permission).order_by(Permission.module.asc(), Permission.id.asc()).all()

    @staticmethod
    def get_by_ids(db: Session, ids: list[int]) -> list[Permission]:
        return db.query(Permission).filter(Permission.id.in_(ids)).all()

    @staticmethod
    def codes_by_user(user: User) -> set[str]:
        """用户最终权限 = 角色权限 ∪ 所有分组权限。"""
        codes = {p.code for p in user.role.permissions}
        for group in user.groups:
            codes |= {p.code for p in group.permissions}
        return codes
