"""对话与统计服务。"""

from sqlalchemy.orm import Session

from ..core import redis_client
from ..core.exceptions import BizError
from ..dao.business_dao import ConversationDao, QuotaDao
from ..dao.user_dao import UserDao
from ..models import User


def list_conversations(db: Session, user: User, **filters) -> tuple[list, int]:
    """管理员看全部；普通用户只能看自己的对话记录。"""
    if user.role.code not in ("super_admin", "admin"):
        filters["user_id"] = user.id
    return ConversationDao.list_page(db, **filters)


def delete_conversation(db: Session, user: User, cid: int) -> None:
    from ..models import Conversation

    row = db.get(Conversation, cid)
    if row is None:
        raise BizError("记录不存在", status_code=404, code=4040)
    if user.role.code not in ("super_admin", "admin") and row.user_id != user.id:
        raise BizError("无权删除他人对话记录", status_code=403, code=4030)
    ConversationDao.delete_by_id(db, cid)


def delete_session(db: Session, user: User, session_id: str) -> int:
    if user.role.code not in ("super_admin", "admin"):
        raise BizError("无权删除会话", status_code=403, code=4030)
    return ConversationDao.delete_by_session(db, session_id)


def overview(db: Session) -> dict:
    users = UserDao.count(db)
    calls = ConversationDao.day_stats(db)
    return {
        "total_users": users["total"],
        "enabled_users": users["enabled"],
        "disabled_users": users["disabled"],
        **calls,
        "online_sessions": _online_count(),
        "rate_limit_per_minute": redis_client.get_rate_limit_config(),
    }


def _online_count() -> int:
    try:
        keys = redis_client.get_redis().keys("auth:sess:*")
        return len(keys)
    except Exception:  # noqa: BLE001
        return 0


def list_quotas(db: Session) -> list[dict]:
    rows = QuotaDao.list_all(db)
    out = []
    for q in rows:
        u = UserDao.get_by_id(db, q.user_id)
        out.append({
            "user_id": q.user_id,
            "username": u.username if u else "(已删除)",
            "daily_limit": q.daily_limit,
            "used_today": q.used_today,
            "used_total": q.used_total,
            "remaining": q.remaining,
            "last_date": q.last_date,
        })
    return out


def update_quota(db: Session, user_id: int, daily_limit: int) -> None:
    user = UserDao.get_by_id(db, user_id)
    if user is None:
        raise BizError("用户不存在", status_code=404, code=4040)
    quota = QuotaDao.get_or_create(db, user_id, daily_limit)
    QuotaDao.update_limit(db, quota, daily_limit)
