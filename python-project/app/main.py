"""Dialogue BFF 入口。

架构：
  浏览器前端 ──HTTPS(SSE)──▶ 本服务（会话管理 / 鉴权 / 限流 / 协议适配）
                                     └──HTTPS POST──▶ 自建服务器模型 API

启动：uvicorn app.main:app --host 127.0.0.1 --port 8000
"""

import asyncio
import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from . import platform
from .config import get_settings
from .models import ChatRequest, SessionDetail, SessionInfo
from .rate_limit import SlidingWindowLimiter
from .sessions import SessionStore
from .sse import keepalive, sse
from .upstream import UpstreamClient, UpstreamError, get_live_config

settings = get_settings()

store = SessionStore(settings.session_ttl_minutes * 60, settings.max_history_messages)
ip_limiter = SlidingWindowLimiter(60, settings.rate_limit_ip_per_minute)
session_limiter = SlidingWindowLimiter(60, settings.rate_limit_session_per_minute)
upstream = UpstreamClient()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await upstream.aclose()


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
    docs_url="/docs" if settings.app_env == "dev" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def client_ip(request: Request) -> str:
    if settings.trust_proxy_headers:
        fwd = request.headers.get("x-forwarded-for", "")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ---------------------------------------------------------------------------
# 基础
# ---------------------------------------------------------------------------
async def authorize_any(request: Request) -> None:
    """通用鉴权：平台 JWT 优先，其次客户端密钥；均无效抛 401/403。"""
    authorization = request.headers.get("authorization", "")
    token = authorization[7:].strip() if authorization.lower().startswith("bearer ") else ""
    if platform.looks_like_jwt(token):
        # 校验平台令牌（黑名单/封禁/状态），无效则抛 401/403
        await platform.platform_auth(token)
    elif token not in settings.allowed_keys:
        raise HTTPException(
            status_code=401,
            detail="缺少有效认证",
            headers={"WWW-Authenticate": "Bearer"},
        )


@app.get("/health")
async def health_root():
    return _health_body()


@app.get("/api/v1/health")
async def health(request: Request):
    """健康检查：与对话接口相同的鉴权（平台 JWT 或客户端密钥）。"""
    await authorize_any(request)
    return _health_body()


def _health_body() -> dict:
    live = get_live_config()
    return {
        "status": "ok",
        "service": settings.app_name,
        "model": live["model"],
        "protocol": live["protocol"],
        "time": time.time(),
    }


# ---------------------------------------------------------------------------
# 会话管理
# ---------------------------------------------------------------------------
@app.get("/api/v1/sessions", response_model=list[SessionInfo])
async def list_sessions(request: Request):
    await authorize_any(request)
    sessions = await store.list()
    return [
        SessionInfo(
            id=s.id,
            title=s.title(),
            message_count=len(s.messages),
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in sessions
    ]


@app.get("/api/v1/sessions/{sid}", response_model=SessionDetail)
async def get_session(sid: str, request: Request):
    await authorize_any(request)
    session = await store.get(sid)
    if session is None:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")
    return SessionDetail(
        id=session.id,
        title=session.title(),
        message_count=len(session.messages),
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=session.messages,
    )


@app.delete("/api/v1/sessions/{sid}", status_code=204)
async def delete_session(sid: str, request: Request):
    await authorize_any(request)
    await store.delete(sid)


# ---------------------------------------------------------------------------
# 对话（SSE 流式）
# 鉴权优先级：平台 JWT（配额/限流/入库） > CLIENT_API_KEYS（开发调试）
# ---------------------------------------------------------------------------
@app.post("/api/v1/chat")
async def chat(req: ChatRequest, request: Request):
    # --- 限流 ---
    ip = client_ip(request)
    if not ip_limiter.allow(f"ip:{ip}"):
        raise HTTPException(
            status_code=429,
            detail="请求过于频繁，请稍后再试",
            headers={"Retry-After": "60"},
        )

    # --- 鉴权：平台 JWT 或客户端密钥 ---
    authorization = request.headers.get("authorization", "")
    platform_user = None
    token = ""
    if authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()

    if platform.looks_like_jwt(token):
        platform_user = await platform.platform_auth(token)
        await platform.enforce_limits(platform_user.id)
    elif token in settings.allowed_keys:
        pass  # 开发/调试模式：客户端密钥直连
    else:
        raise HTTPException(
            status_code=401,
            detail="缺少有效认证（平台 JWT 或客户端密钥）",
            headers={"WWW-Authenticate": "Bearer"},
        )

    sid = request.headers.get("x-session-id")
    session = await store.get_or_create(sid)
    if sid and not session_limiter.allow(f"session:{session.id}"):
        raise HTTPException(
            status_code=429,
            detail="该会话请求过于频繁，请稍后再试",
            headers={"Retry-After": "30"},
        )

    # --- 会话落库（用户消息先行持久化，流开始前完成）---
    for m in req.messages:
        await store.append(session, m.role, m.content)
    history = session.messages[-settings.max_history_messages:]

    params = {
        # 模型名实时读取（管理平台「模型接入」可改，无需重启）
        "model": req.model or get_live_config()["model"],
        "temperature": req.temperature,
        "max_tokens": req.max_tokens,
    }

    async def event_stream() -> AsyncIterator[str]:
        request_id = uuid.uuid4().hex[:12]
        yield sse("meta", {
            "session_id": session.id,
            "request_id": request_id,
            "model": params["model"],
        })

        assistant_parts: list[str] = []
        finish_reason = "stop"
        usage: dict = {}
        ait = upstream.stream(history, params)

        try:
            while True:
                try:
                    # 上游静默超过 keepalive 间隔时输出 SSE 注释防断连
                    ev = await asyncio.wait_for(
                        anext(ait), timeout=settings.keepalive_seconds
                    )
                except asyncio.TimeoutError:
                    yield keepalive()
                    continue
                except StopAsyncIteration:
                    break

                if ev.error:
                    raise UpstreamError(ev.error)
                if ev.delta:
                    assistant_parts.append(ev.delta)
                    yield sse("delta", {"content": ev.delta})
                if ev.done:
                    finish_reason = ev.finish_reason or finish_reason
                    usage = ev.usage or usage
                    break

            text = "".join(assistant_parts)
            if text:
                await store.append(session, "assistant", text)
            # 平台用户：对话入库 + 配额扣减 + AI 调用审计
            if platform_user is not None:
                await asyncio.to_thread(
                    platform.record_chat,
                    user=platform_user,
                    model=params["model"],
                    prompt=req.messages[-1].content if req.messages else "",
                    answer=text,
                    tokens=int(usage.get("total_tokens") or 0),
                    session_id=session.id,
                    ip=ip,
                )
            yield sse("done", {
                "session_id": session.id,
                "finish_reason": finish_reason,
                "usage": usage,
            })

        except asyncio.CancelledError:
            # 浏览器断开：保留已生成的部分内容
            partial = "".join(assistant_parts)
            if partial:
                await store.append(session, "assistant", partial)
            raise
        except UpstreamError as exc:
            partial = "".join(assistant_parts)
            if partial:
                await store.append(session, "assistant", partial)
            yield sse("error", {"message": str(exc), "code": "upstream_error"})
        except Exception as exc:  # 兜底，避免流中断时无任何提示
            yield sse("error", {"message": f"服务内部错误: {exc}", "code": "internal_error"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Nginx 反代下禁用缓冲，保证逐字输出
            "X-RateLimit-Limit": str(settings.rate_limit_ip_per_minute),
        },
    )
