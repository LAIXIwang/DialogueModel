"""DAO：用户分组。"""

from sqlalchemy.orm import Session

from ..models import Permission, User, UserGroup


class GroupDao:
    @staticmethod
    def get_by_id(db: Session, group_id: int) -> UserGroup | None:
        return db.get(UserGroup, group_id)

    @staticmethod
    def get_by_name(db: Session, name: str) -> UserGroup | None:
        return db.query(UserGroup).filter(UserGroup.name == name).first()

    @staticmethod
    def list_all(db: Session) -> list[UserGroup]:
        return db.query(UserGroup).order_by(UserGroup.id.asc()).all()

    @staticmethod
    def create(db: Session, name: str, description: str) -> UserGroup:
        group = UserGroup(name=name, description=description)
        db.add(group)
        db.commit()
        db.refresh(group)
        return group

    @staticmethod
    def update(db: Session, group: UserGroup, name: str | None, description: str | None) -> None:
        if name is not None:
            group.name = name
        if description is not None:
            group.description = description
        db.commit()

    @staticmethod
    def delete(db: Session, group: UserGroup) -> None:
        db.delete(group)
        db.commit()

    @staticmethod
    def set_members(db: Session, group: UserGroup, user_ids: list[int]) -> None:
        """统一分配：把分组成员整体替换为所选用户。"""
        group.users = db.query(User).filter(User.id.in_(user_ids)).all()
        db.commit()

    @staticmethod
    def set_permissions(db: Session, group: UserGroup, permission_ids: list[int]) -> None:
        """统一分配：给分组整体分配权限。"""
        group.permissions = db.query(Permission).filter(Permission.id.in_(permission_ids)).all()
        db.commit()
