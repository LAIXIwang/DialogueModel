"""DAO：对话记录 / 配额 / 审计日志。"""

from datetime import datetime, timedelta

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..models import ApiQuota, Conversation, OperateLog


class ConversationDao:
    @staticmethod
    def list_page(
        db: Session,
        page: int,
        size: int,
        user_id: int | None = None,
        keyword: str = "",
        model: str = "",
        start: str = "",
        end: str = "",
    ) -> tuple[list[Conversation], int]:
        q = db.query(Conversation)
        if user_id is not None:
            q = q.filter(Conversation.user_id == user_id)
        if keyword:
            like = f"%{keyword}%"
            q = q.filter(or_(Conversation.prompt.like(like), Conversation.answer.like(like)))
        if model:
            q = q.filter(Conversation.model == model)
        if start:
            q = q.filter(Conversation.created_at >= datetime.fromisoformat(start))
        if end:
            q = q.filter(Conversation.created_at <= datetime.fromisoformat(end))
        total = q.count()
        items = q.order_by(Conversation.id.desc()).offset((page - 1) * size).limit(size).all()
        return items, total

    @staticmethod
    def create(
        db: Session,
        *,
        user_id: int | None,
        username: str,
        model: str,
        prompt: str,
        answer: str,
        tokens: int,
        session_id: str,
        ip: str,
    ) -> Conversation:
        row = Conversation(
            user_id=user_id,
            username=username,
            model=model,
            prompt=prompt[:20000],
            answer=answer[:200000],
            tokens=tokens,
            session_id=session_id,
            ip=ip,
        )
        db.add(row)
        db.commit()
        return row

    @staticmethod
    def delete_by_id(db: Session, cid: int) -> bool:
        row = db.get(Conversation, cid)
        if row is None:
            return False
        db.delete(row)
        db.commit()
        return True

    @staticmethod
    def delete_by_session(db: Session, session_id: str) -> int:
        n = db.query(Conversation).filter(Conversation.session_id == session_id).delete()
        db.commit()
        return n

    @staticmethod
    def day_stats(db: Session) -> dict:
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today = db.query(Conversation).filter(Conversation.created_at >= today_start)
        return {
            "today_calls": today.count(),
            "today_tokens": today.with_entities(func.coalesce(func.sum(Conversation.tokens), 0)).scalar(),
            "total_calls": db.query(Conversation).count(),
            "total_tokens": db.query(Conversation).with_entities(func.coalesce(func.sum(Conversation.tokens), 0)).scalar(),
        }


class QuotaDao:
    @staticmethod
    def get_by_user(db: Session, user_id: int) -> ApiQuota | None:
        return db.query(ApiQuota).filter(ApiQuota.user_id == user_id).first()

    @staticmethod
    def get_or_create(db: Session, user_id: int, default_limit: int) -> ApiQuota:
        quota = QuotaDao.get_by_user(db, user_id)
        if quota is None:
            quota = ApiQuota(user_id=user_id, daily_limit=default_limit)
            db.add(quota)
            db.commit()
            db.refresh(quota)
        return quota

    @staticmethod
    def reset_if_new_day(quota: ApiQuota, today: str) -> None:
        if quota.last_date != today:
            quota.last_date = today
            quota.used_today = 0

    @staticmethod
    def deduct(db: Session, quota: ApiQuota, tokens: int) -> None:
        QuotaDao.reset_if_new_day(quota, datetime.now().strftime("%Y-%m-%d"))
        quota.used_today += tokens
        quota.used_total += tokens
        db.commit()

    @staticmethod
    def update_limit(db: Session, quota: ApiQuota, daily_limit: int) -> None:
        quota.daily_limit = daily_limit
        db.commit()

    @staticmethod
    def list_all(db: Session) -> list[ApiQuota]:
        return db.query(ApiQuota).order_by(ApiQuota.used_total.desc()).all()


class LogDao:
    @staticmethod
    def list_page(
        db: Session,
        page: int,
        size: int,
        action: str = "",
        username: str = "",
        ip: str = "",
        start: str = "",
        end: str = "",
    ) -> tuple[list[OperateLog], int]:
        q = db.query(OperateLog)
        if action:
            q = q.filter(OperateLog.action == action)
        if username:
            q = q.filter(OperateLog.username.like(f"%{username}%"))
        if ip:
            q = q.filter(OperateLog.ip.like(f"%{ip}%"))
        if start:
            q = q.filter(OperateLog.created_at >= datetime.fromisoformat(start))
        if end:
            q = q.filter(OperateLog.created_at <= datetime.fromisoformat(end))
        total = q.count()
        items = q.order_by(OperateLog.id.desc()).offset((page - 1) * size).limit(size).all()
        return items, total
