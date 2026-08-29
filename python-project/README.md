# Dialogue BFF — 后端应用层

对话系统的 **BFF（Backend For Frontend）/ 应用后端层**，承担会话管理、鉴权、限流与协议适配。

```
┌──────────────────┐      HTTPS (SSE)      ┌──────────────────────────────┐      HTTPS POST      ┌────────────────────┐
│  浏览器前端        │ ───────────────────▶ │  Dialogue BFF（本服务）          │ ─────────────────▶ │  自建服务器模型 API   │
│  vue-project      │  event: meta/delta/  │  会话管理 · 鉴权 · 限流 · 协议适配 │  stream: true      │  vLLM / SGLang /    │
│  (App.vue)        │  done/error         │  FastAPI · Python              │  OpenAI/llama.cpp  │  Ollama / llama.cpp │
└──────────────────┘ ◀─────────────────── └──────────────────────────────┘ ◀───────────────── └────────────────────┘
```

## 特性

| 能力 | 实现 |
| --- | --- |
| 会话管理 | 内存会话存储（TTL 清理、上下文截断），`GET/DELETE /api/v1/sessions` |
| 鉴权 | 浏览器端 Bearer 令牌（`CLIENT_API_KEYS`，常量时间比较）；上游密钥仅存服务端 |
| 限流 | 滑动窗口限流（按 IP + 按会话），返回 `429 + Retry-After` |
| 协议适配 | 适配器模式：`openai`（OpenAI 兼容）、`llamacpp`（原生 /completion），可扩展 |
| 流式输出 | SSE（`meta / delta / done / error`），带 keep-alive 防代理断连 |

## 快速开始（conda work 环境）

```bat
:: 1) 创建/更新 conda work 环境（已存在则只装依赖）
conda env create -f environment.yml
:: 或对已有 work 环境：
conda activate work && pip install -r requirements.txt

:: 2) 配置
copy .env.example .env
::    编辑 .env：UPSTREAM_BASE_URL 指向自建模型 API，CLIENT_API_KEYS 与前端一致

:: 3) 无真实模型时，可先启动模拟上游（另开一个终端）
conda activate work
uvicorn tools.mock_upstream:app --host 127.0.0.1 --port 9190

:: 4) 启动 BFF
run.bat
:: 或：conda activate work && uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

验证：

```bat
curl http://127.0.0.1:8000/api/v1/health -H "Authorization: Bearer sk-bff-demo-key"

curl -N http://127.0.0.1:8000/api/v1/chat ^
  -H "Authorization: Bearer sk-bff-demo-key" ^
  -H "Content-Type: application/json" ^
  -d "{\"messages\":[{\"role\":\"user\",\"content\":\"你好\"}]}"
```

## 浏览器 → BFF 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/v1/health` | 健康检查 |
| POST | `/api/v1/chat` | 对话（SSE 流式），请求头可选 `X-Session-Id` |
| GET | `/api/v1/sessions` | 会话列表 |
| GET | `/api/v1/sessions/{id}` | 会话详情（含历史消息） |
| DELETE | `/api/v1/sessions/{id}` | 删除会话 |

对话请求体（OpenAI 风格，BFF 自动合并会话历史）：

```json
{ "messages": [ { "role": "user", "content": "你好" } ], "model": "可选", "stream": true }
```

SSE 事件协议：

```
event: meta   data: {"session_id": "...", "request_id": "...", "model": "..."}
event: delta  data: {"content": "增量文本"}
event: done   data: {"session_id": "...", "finish_reason": "stop", "usage": {}}
event: error  data: {"message": "...", "code": "upstream_error"}
```

## 环境变量

完整清单见 [.env.example](.env.example)，关键项：

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `CLIENT_API_KEYS` | `sk-bff-demo-key` | 浏览器端令牌，逗号分隔 |
| `UPSTREAM_BASE_URL` | `http://127.0.0.1:9190/v1` | 自建模型 API 地址，生产用 `https://` |
| `UPSTREAM_API_KEY` | 空 | 上游密钥（仅服务端持有） |
| `UPSTREAM_PROTOCOL` | `openai` | `openai` 或 `llamacpp` |
| `UPSTREAM_MODEL` | `dialogue-model` | 默认模型名 |
| `RATE_LIMIT_IP_PER_MINUTE` | 30 | 每 IP 每分钟请求上限 |
| `RATE_LIMIT_SESSION_PER_MINUTE` | 15 | 每会话每分钟请求上限 |
| `MAX_HISTORY_MESSAGES` | 40 | 带入模型的上下文条数 |
| `CORS_ORIGINS` | `localhost:5173` | 允许的前端来源 |

## 接入模型 API

当前 `.env` 已配置 **DeepSeek**（OpenAI 兼容协议，无需改代码）：

```ini
UPSTREAM_BASE_URL=https://api.deepseek.com
UPSTREAM_API_KEY=sk-...
UPSTREAM_PROTOCOL=openai
UPSTREAM_MODEL=deepseek-chat      # 或 deepseek-reasoner
```

1. **OpenAI 兼容服务**（DeepSeek / vLLM / SGLang / Ollama / LMDeploy 等，推荐）：
   ```ini
   UPSTREAM_PROTOCOL=openai
   UPSTREAM_BASE_URL=https://api.deepseek.com      # 自建服务则填 https://your-model-host:port/v1
   UPSTREAM_MODEL=deepseek-chat
   ```
2. **llama.cpp 原生协议**：`UPSTREAM_PROTOCOL=llamacpp`（适配器自动将 messages 拼装为 prompt）。
3. **其他自定义协议**：在 `app/adapters/` 新增实现 `BaseAdapter` 的子类并注册，即可接入任何返回 SSE 的模型服务。

## 生产部署要点

- **TLS**：由 Nginx / Caddy 等在 BFF 之前终止 HTTPS，浏览器与 BFF 之间即「HTTPS(SSE)」；
  Nginx 需配置 `proxy_buffering off;`（BFF 已返回 `X-Accel-Buffering: no`）。
- **密钥**：定期轮换 `CLIENT_API_KEYS`（新旧并存滚动切换）；上游密钥只放服务端环境。
- **限流扩展**：多实例部署时将 `app/rate_limit.py` 替换为 Redis 实现（接口不变）。
- **会话持久化**：多实例部署时将 `app/sessions.py` 替换为 Redis/数据库实现。
- **审计**：生产建议为 `/api/v1/chat` 增加访问日志与请求 ID 追踪（`meta` 事件含 `request_id`）。

## 目录结构

```
python-project/
├─ app/
│  ├─ main.py            # FastAPI 入口：路由 + SSE 流式组装
│  ├─ config.py          # pydantic-settings 集中配置
│  ├─ auth.py            # Bearer 令牌鉴权
│  ├─ rate_limit.py      # 滑动窗口限流
│  ├─ sessions.py        # 会话存储
│  ├─ sse.py             # SSE 事件协议
│  ├─ upstream.py        # 上游 HTTPS POST 客户端
│  ├─ models.py          # 请求/响应模型
│  └─ adapters/          # 协议适配层（openai / llamacpp）
├─ tools/mock_upstream.py  # 模拟模型 API（联调用）
├─ environment.yml       # conda work 环境定义
├─ requirements.txt
├─ .env.example
└─ run.bat
```
