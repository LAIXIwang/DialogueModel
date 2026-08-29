# vue-project

Dialogue 对话前端：黑色主题、简洁可商用的 AI 对话界面（Vue 3 + Vite）。

对话逻辑全部在 `src/App.vue`：

- SSE 流式对话（fetch + ReadableStream 解析 `meta/delta/done/error` 事件）
- 会话列表 / 新建 / 删除 / 历史回看（持久化到 BFF）
- 连接配置集中在 `src/config.js`（BFF 地址、客户端令牌、模型名）
- Markdown 渲染（marked + DOMPurify 消毒）、复制、停止生成、中文输入法安全发送
- 鉴权：`Authorization: Bearer <客户端令牌>`；会话：`X-Session-Id` 请求头

## 与 BFF 对接

开发环境默认请求 `/api`，由 Vite 代理转发到本地 BFF（`vite.config.js`）：

```
http://localhost:5173/api/...  →  http://127.0.0.1:8000/api/...
```

生产环境将 `src/config.js` 中的 `API_BASE` 改为完整地址
（如 `https://bff.example.com/api`），并同步 `API_KEY` 与 BFF 的
`CLIENT_API_KEYS`。

## Recommended IDE Setup

[VS Code](https://code.visualstudio.com/) + [Vue (Official)](https://marketplace.visualstudio.com/items?itemName=Vue.volar) (and disable Vetur).

## Recommended Browser Setup

- Chromium-based browsers (Chrome, Edge, Brave, etc.):
  - [Vue.js devtools](https://chromewebstore.google.com/detail/vuejs-devtools/nhdogjmejiglipccpnnnanhbledajbpd)
  - [Turn on Custom Object Formatter in Chrome DevTools](http://bit.ly/object-formatters)
- Firefox:
  - [Vue.js devtools](https://addons.mozilla.org/en-US/firefox/addon/vue-js-devtools/)
  - [Turn on Custom Object Formatter in Firefox DevTools](https://fxdx.dev/firefox-devtools-custom-object-formatters/)

## Customize configuration

See [Vite Configuration Reference](https://vite.dev/config/).

## Project Setup

```sh
npm install
```

### Compile and Hot-Reload for Development

```sh
npm run dev
```

### Compile and Minify for Production

```sh
npm run build
```

### Run Unit Tests with [Vitest](https://vitest.dev/)

```sh
npm run test:unit
```

### Run End-to-End Tests with [Playwright](https://playwright.dev)

```sh
# Install browsers for the first run
npx playwright install

# When testing on CI, must build the project first
npm run build

# Runs the end-to-end tests
npm run test:e2e
# Runs the tests only on Chromium
npm run test:e2e -- --project=chromium
# Runs the tests of a specific file
npm run test:e2e -- tests/example.spec.ts
# Runs the tests in debug mode
npm run test:e2e -- --debug
```

### Lint with [ESLint](https://eslint.org/)

```sh
npm run lint
```
