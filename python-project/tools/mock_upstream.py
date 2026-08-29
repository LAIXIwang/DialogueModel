"""模拟自建模型 API（OpenAI 兼容协议）。

用于在没有真实推理服务时联调整条链路：
  conda activate work
  uvicorn tools.mock_upstream:app --host 127.0.0.1 --port 9190

真实部署时把它替换为 vLLM / SGLang / Ollama 等服务的地址即可。
"""

import asyncio
import json

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI(title="Mock Model API")


class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "dialogue-model"
    messages: list[Message]
    stream: bool = True


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest):
    last_user = next((m.content for m in reversed(req.messages) if m.role == "user"), "")
    reply = (
        f"这是模拟模型的回复。\n\n"
        f"我收到了你的消息：「{last_user[:60]}」\n\n"
        f"- 本服务模拟 **OpenAI 兼容协议** 的流式输出\n"
        f"- 当前模型：`{req.model}`\n"
        f"- 架构：浏览器 → BFF(SSE) → 模型 API(HTTPS POST)\n\n"
        f"将 `UPSTREAM_BASE_URL` 指向真实推理服务即可接入自建模型。"
    )

    async def gen():
        # 模拟 DeepSeek 推理模型：先输出思维链草稿（BFF 应过滤，前端不展示）
        reasoning = "（内部思考草稿：用户想知道架构，我先组织一下回答要点……）"
        r_chunk = {
            "id": "mock-1",
            "object": "chat.completion.chunk",
            "model": req.model,
            "choices": [{"index": 0, "delta": {"reasoning_content": reasoning}, "finish_reason": None}],
        }
        yield f"data: {json.dumps(r_chunk, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.2)

        # 按句子切片逐字输出，模拟真实推理延迟
        for ch in reply:
            chunk = {
                "id": "mock-1",
                "object": "chat.completion.chunk",
                "model": req.model,
                "choices": [{"index": 0, "delta": {"content": ch}, "finish_reason": None}],
            }
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.015)
        final = {
            "id": "mock-1",
            "object": "chat.completion.chunk",
            "model": req.model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 12, "completion_tokens": len(reply), "total_tokens": 12 + len(reply)},
        }
        yield f"data: {json.dumps(final, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")
