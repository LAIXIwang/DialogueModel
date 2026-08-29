"""DAO：用户表。"""

from datetime import datetime

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..models import User


class UserDao:
    @staticmethod
    def get_by_id(db: Session, user_id: int) -> User | None:
        return db.get(User, user_id)

    @staticmethod
    def get_by_username(db: Session, username: str) -> User | None:
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def get_by_ids(db: Session, ids: list[int]) -> list[User]:
        if not ids:
            return []
        return db.query(User).filter(User.id.in_(ids)).all()

    @staticmethod
    def list_page(
        db: Session,
        page: int,
        size: int,
        keyword: str = "",
        status: int | None = None,
        role_id: int | None = None,
    ) -> tuple[list[User], int]:
        q = db.query(User)
        if keyword:
            like = f"%{keyword}%"
            q = q.filter(
                or_(User.username.like(like), User.phone.like(like), User.email.like(like))
            )
        if status is not None:
            q = q.filter(User.status == status)
        if role_id is not None:
            q = q.filter(User.role_id == role_id)
        total = q.count()
        items = (
            q.order_by(User.id.desc()).offset((page - 1) * size).limit(size).all()
        )
        return items, total

    @staticmethod
    def create(db: Session, username: str, password_hash: str, role_id: int, phone: str, email: str) -> User:
        user = User(
            username=username,
            password_hash=password_hash,
            role_id=role_id,
            phone=phone,
            email=email,
            status=1,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def update_last_login(db: Session, user: User) -> None:
        user.last_login_at = datetime.now()
        db.commit()

    @staticmethod
    def update_status(db: Session, user: User, status: int) -> None:
        user.status = status
        db.commit()

    @staticmethod
    def update_password(db: Session, user: User, password_hash: str) -> None:
        user.password_hash = password_hash
        db.commit()

    @staticmethod
    def update_profile(db: Session, user: User, **fields) -> None:
        for k, v in fields.items():
            if v is not None:
                setattr(user, k, v)
        db.commit()

    @staticmethod
    def assign_role(db: Session, user: User, role_id: int) -> None:
        user.role_id = role_id
        db.commit()

    @staticmethod
    def count(db: Session) -> dict:
        return {
            "total": db.query(User).count(),
            "enabled": db.query(User).filter(User.status == 1).count(),
            "disabled": db.query(User).filter(User.status == 0).count(),
        }
