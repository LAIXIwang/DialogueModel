"""OpenAI 兼容协议适配器。

适用于绝大多数自建推理服务：vLLM、SGLang、LMDeploy、Ollama、
llama.cpp server（OpenAI 兼容模式）、DeepSeek 本地部署等。
"""

import json
from typing import Any

from .base import AdapterEvent, BaseAdapter


class OpenAICompatAdapter(BaseAdapter):
    name = "openai"

    def build_request(
        self,
        messages: list[dict],
        params: dict[str, Any],
        base_url: str,
    ) -> tuple[str, dict]:
        base = base_url.rstrip("/")
        url = base if base.endswith("/chat/completions") else f"{base}/chat/completions"
        payload: dict[str, Any] = {
            "model": params.get("model"),
            "messages": messages,
            "stream": True,
        }
        if params.get("temperature") is not None:
            payload["temperature"] = params["temperature"]
        if params.get("max_tokens") is not None:
            payload["max_tokens"] = params["max_tokens"]
        return url, payload

    def parse_data(self, payload: str) -> AdapterEvent | None:
        text = payload.strip()
        if text == "[DONE]":
            return AdapterEvent(done=True, finish_reason="stop")

        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            return None

        if not isinstance(obj, dict):
            return None

        # 上游以流内 JSON 形式返回错误
        if obj.get("error"):
            err = obj["error"]
            msg = err.get("message") if isinstance(err, dict) else str(err)
            return AdapterEvent(error=msg or "上游返回未知错误")

        choices = obj.get("choices") or []
        if not choices:
            return None

        choice = choices[0]
        finish_reason = choice.get("finish_reason")
        delta = choice.get("delta") or {}
        content = delta.get("content")

        if finish_reason:
            usage = obj.get("usage") or {}
            return AdapterEvent(done=True, finish_reason=finish_reason, usage=usage)

        # 只输出最终回答 content；模型的内部思考（reasoning_content 思维链草稿）
        # 一律丢弃，不进入 SSE 流、不展示给用户
        if isinstance(content, str) and content:
            return AdapterEvent(delta=content)
        return None
