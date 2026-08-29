"""会话&对话管理、配额统计、审计日志接口。"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from ..core import redis_client
from ..core.audit import record_log
from ..core.deps import client_ip, get_current_user, require_permission
from ..core.exceptions import BizError, ok
from ..database import get_db
from ..dao.business_dao import LogDao
from ..models import User
from ..schemas import UpdateQuotaRequest, UpdateRateLimitRequest
from ..services import conversation_service

conv_router = APIRouter(prefix="/api/conversations", tags=["会话管理"])
stats_router = APIRouter(prefix="/api/stats", tags=["调用统计"])
quota_router = APIRouter(prefix="/api/quotas", tags=["配额管控"])
log_router = APIRouter(prefix="/api/logs", tags=["审计日志"])


def _conv_out(c) -> dict:
    return {
        "id": c.id,
        "user_id": c.user_id,
        "username": c.username,
        "model": c.model,
        "prompt": c.prompt,
        "answer": c.answer,
        "tokens": c.tokens,
        "session_id": c.session_id,
        "ip": c.ip,
        "created_at": c.created_at.isoformat(),
    }


# ------------------------------ 会话 & 对话 ------------------------------
@conv_router.get("")
def list_conversations(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    user_id: int | None = None,
    keyword: str = "",
    model: str = "",
    start: str = "",
    end: str = "",
    user: User = Depends(require_permission("conversation:list")),
    db: Session = Depends(get_db),
):
    items, total = conversation_service.list_conversations(
        db, user, page=page, size=size, user_id=user_id, keyword=keyword, model=model, start=start, end=end
    )
    return ok({"total": total, "items": [_conv_out(c) for c in items]})


@conv_router.delete("/{cid}")
def delete_conversation(
    cid: int,
    request: Request,
    user: User = Depends(require_permission("conversation:delete")),
    db: Session = Depends(get_db),
):
    conversation_service.delete_conversation(db, user, cid)
    record_log(db, "conversation.delete", ip=client_ip(request), user_id=user.id, username=user.username,
               params={"conversation_id": cid})
    return ok(message="删除成功")


@conv_router.delete("/session/{session_id}")
def delete_session(
    session_id: str,
    request: Request,
    user: User = Depends(require_permission("conversation:delete")),
    db: Session = Depends(get_db),
):
    n = conversation_service.delete_session(db, user, session_id)
    record_log(db, "session.delete", ip=client_ip(request), user_id=user.id, username=user.username,
               params={"session_id": session_id, "rows": n})
    return ok(message=f"已删除 {n} 条记录")


# ------------------------------ 调用统计 ------------------------------
@stats_router.get("/overview")
def stats_overview(_: User = Depends(require_permission("stats:read")), db: Session = Depends(get_db)):
    return ok(conversation_service.overview(db))


# ------------------------------ 配额管控 ------------------------------
@quota_router.get("")
def list_quotas(_: User = Depends(require_permission("quota:read")), db: Session = Depends(get_db)):
    return ok(conversation_service.list_quotas(db))


@quota_router.put("/{user_id}")
def update_quota(
    user_id: int,
    req: UpdateQuotaRequest,
    request: Request,
    operator: User = Depends(require_permission("quota:edit")),
    db: Session = Depends(get_db),
):
    conversation_service.update_quota(db, user_id, req.daily_limit)
    record_log(db, "quota.edit", ip=client_ip(request), user_id=operator.id, username=operator.username,
               params={"target_user": user_id, "daily_limit": req.daily_limit})
    return ok(message="配额已更新")


# ------------------------------ 限流配置 ------------------------------
@stats_router.get("/rate-limit")
def get_rate_limit(_: User = Depends(require_permission("quota:edit")),):
    return ok({"per_minute": redis_client.get_rate_limit_config()})


@stats_router.put("/rate-limit")
def set_rate_limit(
    req: UpdateRateLimitRequest,
    request: Request,
    operator: User = Depends(require_permission("quota:edit")),
    db: Session = Depends(get_db),
):
    redis_client.set_rate_limit_config(req.per_minute)
    record_log(db, "ratelimit.update", ip=client_ip(request), user_id=operator.id,
               username=operator.username, params={"per_minute": req.per_minute})
    return ok(message=f"单用户限流已调整为每分钟 {req.per_minute} 次")


# ------------------------------ 审计日志 ------------------------------
@log_router.get("")
def list_logs(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    action: str = "",
    username: str = "",
    ip: str = "",
    start: str = "",
    end: str = "",
    _: User = Depends(require_permission("log:read")),
    db: Session = Depends(get_db),
):
    items, total = LogDao.list_page(db, page, size, action, username, ip, start, end)
    return ok({
        "total": total,
        "items": [
            {
                "id": x.id,
                "user_id": x.user_id,
                "username": x.username,
                "action": x.action,
                "ip": x.ip,
                "params": x.params,
                "detail": x.detail,
                "created_at": x.created_at.isoformat(),
            }
            for x in items
        ],
    })


@log_router.get("/actions")
def list_actions(_: User = Depends(require_permission("log:read"))):
    return ok([
        {"value": "login", "label": "登录"},
        {"value": "login.fail", "label": "登录失败"},
        {"value": "logout", "label": "登出"},
        {"value": "register", "label": "注册"},
        {"value": "token.refresh", "label": "刷新令牌"},
        {"value": "password.change", "label": "修改密码"},
        {"value": "user.create", "label": "创建用户"},
        {"value": "user.edit", "label": "编辑用户"},
        {"value": "user.disable", "label": "禁用用户"},
        {"value": "user.enable", "label": "启用用户"},
        {"value": "user.reset_password", "label": "重置密码"},
        {"value": "user.assign_role", "label": "分配角色"},
        {"value": "user.delete", "label": "删除用户"},
        {"value": "role.create", "label": "创建角色"},
        {"value": "role.edit", "label": "编辑角色"},
        {"value": "role.delete", "label": "删除角色"},
        {"value": "role.assign_permission", "label": "角色分配权限"},
        {"value": "conversation.delete", "label": "删除对话"},
        {"value": "session.delete", "label": "删除会话"},
        {"value": "quota.edit", "label": "调整配额"},
        {"value": "ratelimit.update", "label": "调整限流"},
        {"value": "ai.call", "label": "AI 调用"},
    ])
