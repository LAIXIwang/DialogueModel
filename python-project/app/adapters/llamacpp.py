"""llama.cpp server 原生 /completion 协议适配器（示例）。

演示如何接入「非 OpenAI 兼容」的自建模型协议：
浏览器侧仍是统一的 messages 结构，由适配器拼装 prompt 并解析
/completion 的流式返回。
"""

import json
from typing import Any

from .base import AdapterEvent, BaseAdapter


class LlamaCppAdapter(BaseAdapter):
    name = "llamacpp"

    def build_request(
        self,
        messages: list[dict],
        params: dict[str, Any],
        base_url: str,
    ) -> tuple[str, dict]:
        url = base_url.rstrip("/") + "/completion"
        payload: dict[str, Any] = {
            "prompt": self._build_prompt(messages),
            "stream": True,
            "n_predict": params.get("max_tokens") or 1024,
            "temperature": params.get("temperature") if params.get("temperature") is not None else 0.7,
            "stop": ["<|user|>", "<|system|>"],
        }
        return url, payload

    def parse_data(self, payload: str) -> AdapterEvent | None:
        try:
            obj = json.loads(payload)
        except json.JSONDecodeError:
            return None
        if not isinstance(obj, dict):
            return None
        if obj.get("error"):
            return AdapterEvent(error=str(obj["error"]))
        if obj.get("stop"):
            return AdapterEvent(done=True, finish_reason="stop")
        content = obj.get("content")
        return AdapterEvent(delta=content) if isinstance(content, str) and content else None

    @staticmethod
    def _build_prompt(messages: list[dict]) -> str:
        parts = []
        for m in messages:
            role = m["role"]
            if role == "system":
                parts.append(f"<|system|>\n{m['content']}")
            elif role == "user":
                parts.append(f"<|user|>\n{m['content']}")
            else:
                parts.append(f"<|assistant|>\n{m['content']}")
        return "\n".join(parts) + "\n<|assistant|>\n"
