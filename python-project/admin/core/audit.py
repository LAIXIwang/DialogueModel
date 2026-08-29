"""审计日志埋点：登录记录 / 后台操作 / AI 调用 / IP 溯源。"""

import json
from datetime import datetime

from sqlalchemy.orm import Session

from ..models import OperateLog


def record_log(
    db: Session,
    action: str,
    ip: str = "",
    user_id: int | None = None,
    username: str = "",
    params: dict | None = None,
    detail: str = "",
) -> None:
    """写操作审计日志（静默失败不影响主流程）。"""
    try:
        entry = OperateLog(
            user_id=user_id,
            username=username,
            action=action,
            ip=ip or "",
            params=json.dumps(params or {}, ensure_ascii=False)[:4000],
            detail=detail[:500],
            created_at=datetime.now(),
        )
        db.add(entry)
        db.commit()
    except Exception:  # noqa: BLE001 - 审计失败不阻断业务
        db.rollback()
