# Dialogue 用户管理平台（Admin Platform）

AI 对话系统的**用户管理平台**：账号 / RBAC / 会话 / 配额限流 / 审计日志。
与对话平台同一代码库（`python-project`），运行在独立端口 **8001**。

```
浏览器 (Vue3 管理后台) ──HTTPS──▶ Admin API (FastAPI :8001)
                                      ├─ MySQL  DialogueModel（用户/角色/权限/对话/配额/日志）
                                      └─ Redis  127.0.0.1:6379（token 黑名单/会话缓存/限流）

对话平台 (BFF :8000) ──携带平台 JWT──▶ 同一 MySQL/Redis：限流 + 配额扣减 + 对话入库
```

## 技术栈

| 项 | 选型 |
| --- | --- |
| Web 框架 | FastAPI |
| ORM / 数据库 | SQLAlchemy 2 + MySQL（库名 `DialogueModel`，utf8mb4） |
| 鉴权 | JWT（access + refresh，HS256），登出/封禁走 **Redis 黑名单** |
| 密码 | bcrypt 哈希，不存明文 |
| 缓存/限流 | Redis：`auth:bl:*` 黑名单、`auth:ban:*` 封禁、`auth:sess:*` 会话缓存、`ratelimit:user:*` 限流 |
| 权限 | RBAC：role / permission / role_permission，接口层 `require_permission` 全局拦截 |

## 数据表（11 张）

| 表 | 内容 |
| --- | --- |
| `user` | 账号、bcrypt 密文、手机/邮箱、角色 ID、启用/禁用、创建/最后登录时间 |
| `role` | 超级管理员 / 管理员 / 普通用户 / 访客 |
| `permission` | 权限编码（`user:list`、`conversation:read`、`rag:upload`…）、名称、模块 |
| `role_permission` | 角色-权限多对多中间表 |
| `user_group` | 用户分组：自定义命名、描述 |
| `user_group_member` | 分组-用户多对多（多选用户统一入组） |
| `group_permission` | 分组-权限多对多（分组级权限统一分配） |
| `model_config` | 模型接入配置：接口地址、密钥、协议、模型名（单行，实时生效） |
| `conversation` | 对话记录：user_id、模型、提问、回答、token 消耗、session_id、时间、IP |
| `api_quota` | 每日 token 上限、今日消耗、累计消耗、剩余额度 |
| `operate_log` | 审计：操作者、行为、IP、参数、时间（登录/后台操作/AI 调用留痕） |

## 模型接入（管理本地大模型接口）

- 「模型接入」模块可在线修改对话 BFF 的上游模型接口：**地址 / 密钥 / 协议 / 模型名**
- 生效链路：管理平台 → MySQL（持久）+ Redis `config:model`（运行时）→ BFF 每次对话实时读取，**无需重启**
- 密钥仅存服务端，前端只回显打码（`****后4位`），留空提交 = 保留原密钥
- 协议支持 `openai`（OpenAI 兼容）与 `llamacpp`（原生 /completion）；修改写入审计日志

## 分组功能（用户权限 = 角色权限 ∪ 分组权限）

- 自定义命名分组；把**多个用户**批量加入分组（多选、整体替换）
- 给分组**统一分配权限**，组内全部成员共享
- 权限校验时取并集：`角色权限 ∪ 所有分组权限`（超级管理员始终全放行）
- 用户管理列表展示每个用户的所属分组

## 快速开始

```bat
:: 前置：MySQL（3306，密码 123456）与 Redis（6379）已运行
:: 1) 依赖（已随 requirements.txt 更新）
conda activate work && pip install -r requirements.txt

:: 2) 初始化建库 + 种子（幂等，可重复执行）
conda run -n work python -m admin.init_db

:: 3) 启动管理平台（:8001）
admin_run.bat

:: 4) 前端
cd ..\vue-project && npm run dev
:: 打开 http://localhost:5173/login  或聊天页左下角「管理平台」入口
```

默认管理员：**admin / Admin@123456**（首次登录后请修改密码）。

## 架构分层

```
admin/
├─ main.py              # 入口：CORS、统一异常、路由挂载、启动自建表+种子
├─ config.py            # MySQL/Redis/JWT/限流/配额 配置（.env 可覆盖）
├─ database.py          # SQLAlchemy engine / Session
├─ init_db.py           # 建库建表 + 种子数据（幂等）
├─ models/              # DAO 层数据模型：User/Role/Permission/Conversation/ApiQuota/OperateLog
├─ dao/                 # DAO 层：user_dao / rbac_dao / business_dao
├─ services/            # 业务层：登录校验/密码校验/RBAC/配额判断/日志埋点
├─ routers/             # 接口层：auth / users / roles / business(会话/统计/配额/日志)
├─ schemas.py           # Pydantic 契约
└─ core/                # 公共组件：JWT、bcrypt、Redis、异常、依赖注入、审计
```

## 核心接口

| 模块 | 接口 |
| --- | --- |
| 认证 | `POST /api/auth/login` `register` `refresh` `logout` `change-password`；`GET /api/auth/me` |
| 用户 | `GET/POST /api/users`，`PUT /api/users/{id}`，`POST /{id}/status` `/{id}/reset-password`，`PUT /{id}/role`，`DELETE /{id}`，`PUT /api/users/me` |
| 角色 | `GET/POST /api/roles`，`PUT/DELETE /api/roles/{id}`，`GET/PUT /api/roles/{id}/permissions` |
| 分组 | `GET/POST /api/groups`，`PUT/DELETE /api/groups/{id}`，`GET/PUT /api/groups/{id}/members`，`GET/PUT /api/groups/{id}/permissions` |
| 权限 | `GET /api/permissions` |
| 会话 | `GET /api/conversations`（分页/按用户/关键词），`DELETE /{id}`，`DELETE /session/{sid}` |
| 统计 | `GET /api/stats/overview`，`GET/PUT /api/stats/rate-limit` |
| 配额 | `GET /api/quotas`，`PUT /api/quotas/{user_id}` |
| 模型接入 | `GET/PUT /api/model-config`（地址/密钥/协议/模型名，保存即时生效） |
| 日志 | `GET /api/logs`（按行为/操作者/IP），`GET /api/logs/actions` |

统一响应：`{code: 0, message, data}`；业务错误 `code != 0`，401/403 由 JWT/RBAC 拦截器抛出。

## 与对话平台（BFF）集成

BFF `/api/v1/chat` 鉴权优先级：**平台 JWT > CLIENT_API_KEYS**。

平台用户登录后拿到的 `access_token` 直接作为聊天接口的 Bearer 令牌：

1. JWT 校验（黑名单 / 封禁 / 状态）→ 401/403
2. Redis 限流：单用户每分钟 N 次（默认 10，管理后台可改）→ 429
3. 每日配额判断（`api_quota.daily_limit`）→ 429「配额用尽」
4. 生成结束：对话写入 `conversation`、按实际 token 扣减配额、写入 `ai.call` 审计

> 仅用 `CLIENT_API_KEYS` 调用时不限流不记账（开发调试通道）。

## 生产部署要点（nginx 已开启）

管理平台与对话 BFF 同源反代，示例配置：

```nginx
# 前端静态资源（vue-project 构建产物 dist/）
location / {
    root   /path/to/vue-project/dist;
    try_files $uri $uri/ /index.html;
}

# 对话 BFF（SSE 必须关缓冲）
location /api/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    proxy_buffering off;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}

# 管理平台 API
location /admin-api/ {
    proxy_pass http://127.0.0.1:8001;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

- 生产必须修改 `.env` 的 `JWT_SECRET`、数据库密码、`ADMIN_ENV=prod`
- 前端生产构建：`npm run build`；`src/api/index.js` 的 baseURL 与代理前缀需与 nginx 一致
- 对象存储（头像/文档）：`user.avatar` 字段已预留，接入 OSS/S3 时在 `PUT /api/users/me` 上传环节补实现
- 多实例部署：限流/黑名单/会话缓存已在 Redis，可水平扩展
