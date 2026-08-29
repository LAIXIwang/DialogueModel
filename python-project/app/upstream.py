"""上游自建模型 API 客户端（HTTPS POST + 流式读取）。

接入配置（地址 / 密钥 / 协议 / 模型）可被管理平台「模型接入」模块实时修改：
管理平台写入 Redis `config:model`，本客户端每次对话实时读取；
Redis 无值时回退到 .env 的 UPSTREAM_* 默认配置。
"""

import json
import os
import sys
from typing import Any, AsyncIterator

import httpx

from .adapters import AdapterEvent, get_adapter
from .config import get_settings

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from admin.core import redis_client  # noqa: E402

# Redis 中保存模型接入配置的 key（与管理平台一致）
MODEL_CONFIG_KEY = "config:model"


def get_live_config() -> dict:
    """当前生效的模型接入配置：Redis 实时配置 > .env 默认值。"""
    settings = get_settings()
    cfg = {
        "base_url": settings.upstream_base_url,
        "api_key": settings.upstream_api_key,
        "protocol": settings.upstream_protocol,
        "model": settings.upstream_model,
    }
    try:
        raw = redis_client.get_redis().get(MODEL_CONFIG_KEY)
        if raw:
            data = json.loads(raw)
            for key, value in data.items():
                if value not in (None, ""):
                    cfg[key] = value
    except Exception:  # noqa: BLE001 - Redis 不可用时回退 .env
        pass
    return cfg


class UpstreamError(Exception):
    """上游调用错误（网络 / HTTP / 协议级错误）。"""


class UpstreamClient:
    def __init__(self) -> None:
        settings = get_settings()
        # 注意：不再在初始化时固定 adapter / 地址 / 密钥，改为每次调用实时读取
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=settings.connect_timeout,
                read=settings.read_timeout,
                write=settings.write_timeout,
                pool=10.0,
            ),
            limits=httpx.Limits(max_connections=32, max_keepalive_connections=16),
        )

    async def stream(
        self,
        messages: list[dict],
        params: dict[str, Any],
    ) -> AsyncIterator[AdapterEvent]:
        cfg = get_live_config()
        adapter = get_adapter(cfg["protocol"])

        call_params = dict(params)
        if not call_params.get("model"):
            call_params["model"] = cfg["model"]

        headers = {"Content-Type": "application/json"}
        if cfg.get("api_key"):
            headers["Authorization"] = f"Bearer {cfg['api_key']}"

        url, payload = adapter.build_request(messages, call_params, cfg["base_url"])
        try:
            async with self._client.stream("POST", url, headers=headers, json=payload) as resp:
                if resp.status_code >= 400:
                    body = (await resp.aread()).decode("utf-8", "replace")[:2000]
                    raise UpstreamError(f"上游模型 API 返回 {resp.status_code}: {body}")
                async for line in resp.aiter_lines():
                    if not line or line.startswith(":"):
                        continue
                    if line.startswith("data:"):
                        line = line[5:].lstrip()
                    event = adapter.parse_data(line)
                    if event is not None:
                        yield event
        except httpx.HTTPError as exc:
            raise UpstreamError(f"上游连接失败: {exc}") from exc

    async def aclose(self) -> None:
        await self._client.aclose()
