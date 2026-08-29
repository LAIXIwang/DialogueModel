"""会话管理：内存会话存储（含 TTL 清理与上下文截断）。

生产多实例部署可替换为 Redis / 数据库实现，保持相同接口即可。
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field


@dataclass
class Session:
    id: str
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    messages: list[dict] = field(default_factory=list)

    def title(self) -> str:
        for m in self.messages:
            if m["role"] == "user":
                t = m["content"].strip().replace("\n", " ")
                return t[:40] + ("…" if len(t) > 40 else "")
        return "新对话"


class SessionStore:
    def __init__(self, ttl_seconds: int, max_messages: int) -> None:
        self.ttl = ttl_seconds
        self.max_messages = max_messages
        self._sessions: dict[str, Session] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(self, sid: str | None) -> Session:
        async with self._lock:
            self._prune()
            if sid and sid in self._sessions:
                return self._sessions[sid]
            session = Session(id=sid or uuid.uuid4().hex[:16])
            self._sessions[session.id] = session
            return session

    async def get(self, sid: str) -> Session | None:
        async with self._lock:
            self._prune()
            return self._sessions.get(sid)

    async def append(self, session: Session, role: str, content: str) -> None:
        content = content.strip()
        if not content:
            return
        async with self._lock:
            session.messages.append({"role": role, "content": content})
            # 上下文截断：只保留最近 N 条
            if len(session.messages) > self.max_messages:
                del session.messages[: len(session.messages) - self.max_messages]
            session.updated_at = time.time()

    async def list(self) -> list[Session]:
        async with self._lock:
            self._prune()
            return sorted(self._sessions.values(), key=lambda s: s.updated_at, reverse=True)

    async def delete(self, sid: str) -> bool:
        async with self._lock:
            return self._sessions.pop(sid, None) is not None

    def _prune(self) -> None:
        cutoff = time.time() - self.ttl
        stale = [sid for sid, s in self._sessions.items() if s.updated_at < cutoff]
        for sid in stale:
            del self._sessions[sid]
