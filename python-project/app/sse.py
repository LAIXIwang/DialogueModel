"""SSE 输出工具。

BFF → 浏览器事件协议：
  event: meta   data: {session_id, request_id, model}
  event: delta  data: {content}
  event: done   data: {session_id, finish_reason, usage}
  event: error  data: {message, code}
"""

import json
from typing import Any


def sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def keepalive() -> str:
    """SSE 注释行：浏览器会忽略，用于防止代理/网关空闲断连。"""
    return ": keep-alive\n\n"
