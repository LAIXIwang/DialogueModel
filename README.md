# DialogueModel — AI 对话系统 + 用户管理平台

```
┌──────────────────┐   HTTPS(SSE)   ┌──────────────────────────┐   HTTPS POST   ┌──────────────────┐
│  对话前端 (Vue3)   │ ────────────▶ │  BFF/应用后端层 (FastAPI)  │ ────────────▶ │  自建模型 API     │
│  vue-project      │  meta/delta/  │  会话·鉴权·限流·协议适配    │  stream:true  │  DeepSeek/vLLM…  │
│  /                │  done/error   │  :8000                   │               │                  │
└──────────────────┘ ◀──────────── └────────────┬─────────────┘ ◀───────────── └──────────────────┘
                                                │ 平台 JWT：限流 + 配额扣减 + 对话入库
┌──────────────────┐   HTTPS(JSON)  ┌───────────▼──────────────┐        ┌──────────────────┐
│  管理后台 (Vue3)   │ ────────────▶ │  用户管理平台 (FastAPI)     │ ────▶ │  MySQL           │
│  vue-project      │  Bearer JWT   │  RBAC·配额·审计·黑名单      │        │  DialogueModel   │
│  /login /admin    │               │  :8001                   │ ────▶ │  Redis 127.0.0.1 │
└──────────────────┘ ◀──────────── └──────────────────────────┘        └──────────────────┘
```

| 模块 | 目录 | 技术 | 职责 |
| --- | --- | --- | --- |
| 对话前端 | `vue-project/src/App.vue` | Vue 3 + Vite | 黑色简洁聊天界面，SSE 流式 |
| 管理后台前端 | `vue-project/src/views/admin/` | Vue 3 + Element-Plus + Axios | 登录/用户/角色/会话/配额/日志 |
| BFF | `python-project/app/` | FastAPI（conda `work`） | 对话代理：SSE、协议适配、平台 JWT 鉴权 |
| 管理平台 | `python-project/admin/` | FastAPI + SQLAlchemy + Redis | 账号/RBAC/配额限流/审计，router-service-dao 分层 |
| 存储 | MySQL `DialogueModel` · Redis `127.0.0.1:6379` | — | 7 张业务表 / token 黑名单 / 限流 / 会话缓存 |

## 快速开始

```bat
:: 0) 前置：MySQL(3306, 密码123456)、Redis(6379) 已运行
:: 1) 初始化数据库 + 种子（幂等）
cd python-project
conda run -n work pip install -r requirements.txt
conda run -n work python -m admin.init_db

:: 2) 启动管理平台（:8001）
admin_run.bat

:: 3) 启动对话 BFF（:8000，DeepSeek 已配置于 .env）
run.bat

:: 4) 前端（另开终端）
cd vue-project
npm install
npm run dev
```

| 入口 | 地址 | 账号 |
| --- | --- | --- |
| 对话平台 | http://localhost:5173 | 需先登录（`/chat-login`，账号与管理平台互通） |
| 管理后台（独立入口） | http://localhost:5173/login | admin / Admin@123456 |

详细文档：[对话 BFF](python-project/README.md) · [管理平台](python-project/admin/README.md) · [前端](vue-project/README.md)

## 🐳 Docker 一键部署（Linux 服务器）

前置：已安装 Docker 与 Docker Compose。

```bash
git clone <你的仓库地址> dialogue && cd dialogue
./deploy.sh          # 一行命令完成构建与启动（等价于 docker compose --env-file .env.docker up -d --build）
```

部署后访问：

| 入口 | 地址 | 说明 |
| --- | --- | --- |
| 对话平台 | `http://<服务器IP>/` | 登录页 `/chat-login` |
| 管理后台 | `http://<服务器IP>/login` | 默认管理员 admin / Admin@123456 |

架构（5 个容器）：`web`(nginx 静态+反代) → `bff`(:8000) / `admin`(:8001) → `mysql`(DialogueModel) + `redis`(黑名单/限流/会话缓存)。
管理平台启动时自动建表+种子；模型接入密钥通过 `.env.docker` 的 `UPSTREAM_API_KEY` 注入（或部署后在后台「模型接入」在线修改）。

常用运维命令：

```bash
docker compose --env-file .env.docker logs -f      # 查看日志
docker compose --env-file .env.docker restart      # 重启
docker compose --env-file .env.docker down         # 停止（数据卷保留）
```

## 发布到 GitHub

```bash
# 本仓库已初始化并完成首次提交，只需关联远端并推送：
git remote add origin https://github.com/<用户名>/<仓库名>.git
git branch -M main
git push -u origin main
```

> 密钥安全：`.env`、`.env.docker` 已被 .gitignore 排除，仓库中只提交 `.env.example` 模板。

## 安全模型

- 管理平台：JWT（access+refresh）+ bcrypt + RBAC；登出/封禁靠 Redis 黑名单
- 对话接口鉴权优先级：**平台 JWT（限流+配额+记账）> CLIENT_API_KEYS（开发通道）**
- 单用户限流：每分钟 N 次（Redis，后台可调）；每日 token 配额（MySQL，后台可调）
- 模型 API 密钥只存服务端；生产环境 TLS 由 Nginx 终止（配置见管理平台 README）
