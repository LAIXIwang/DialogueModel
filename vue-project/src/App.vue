<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

import { API_BASE, API_KEY, DEFAULT_MODEL } from './config.js'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'

const auth = useAuthStore()

/* ---------------------------------- 常量 ---------------------------------- */
const SESSION_LIST_KEY = 'dialogue.sessionList'
const CURRENT_SESSION_KEY = 'dialogue.currentSession'

/* ---------------------------------- 状态 ---------------------------------- */
const messages = ref([]) // { id, role: 'user'|'assistant', content, pending? }
const sessions = ref([]) // { id, title, updatedAt }
const currentSessionId = ref(localStorage.getItem(CURRENT_SESSION_KEY) || '')
const draft = ref('')
const streaming = ref(false)
const banner = ref('') // 顶部错误提示
const toastMsg = ref('')
const status = ref('checking') // checking | online | offline

const sidebarOpen = ref(window.innerWidth > 900)
const msgScroll = ref(null)
const textareaEl = ref(null)

let abortCtrl = null
let toastTimer = null
let msgSeq = 0

const canSend = computed(() => draft.value.trim().length > 0 && !streaming.value)
const modelLabel = DEFAULT_MODEL || '默认模型'

/* -------------------------------- 工具函数 -------------------------------- */
function uid() {
  return `${Date.now().toString(36)}-${++msgSeq}`
}

function toast(text) {
  toastMsg.value = text
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => (toastMsg.value = ''), 2200)
}

function renderMd(text) {
  if (!text) return ''
  return DOMPurify.sanitize(marked.parse(text, { breaks: true, gfm: true }))
}

function fmtTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  const today = new Date()
  const sameDay = d.toDateString() === today.toDateString()
  const hhmm = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  return sameDay ? hhmm : `${d.getMonth() + 1}/${d.getDate()} ${hhmm}`
}

function scrollToBottom() {
  nextTick(() => {
    const el = msgScroll.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

function chatUrl() {
  return `${API_BASE.replace(/\/+$/, '')}/v1/chat`
}

function authHeaders(extra = {}) {
  const headers = { 'Content-Type': 'application/json', ...extra }
  // 平台 JWT 优先（对话记录/配额记入该用户），未登录时回退客户端密钥
  const token = auth.accessToken || API_KEY
  if (token) headers.Authorization = `Bearer ${token}`
  if (currentSessionId.value) headers['X-Session-Id'] = currentSessionId.value
  return headers
}

/* ------------------------------ 会话列表持久化 ------------------------------ */
function persistSessionList() {
  localStorage.setItem(SESSION_LIST_KEY, JSON.stringify(sessions.value.slice(0, 100)))
}

function upsertSession(sid, title) {
  const idx = sessions.value.findIndex((s) => s.id === sid)
  if (idx >= 0) {
    sessions.value[idx].updatedAt = Date.now()
    if (title) sessions.value[idx].title = title
  } else {
    sessions.value.unshift({ id: sid, title: title || '新对话', updatedAt: Date.now() })
  }
  persistSessionList()
}

/* -------------------------------- SSE 解析 -------------------------------- */
// 将一段原始 SSE 文本解析为 { event, data }
function parseSseBlock(block) {
  let event = 'message'
  const dataLines = []
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim() || 'message'
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart())
  }
  if (dataLines.length === 0) return null
  return { event, data: dataLines.join('\n') }
}

/* -------------------------------- 核心：发送 -------------------------------- */
async function send() {
  const text = draft.value.trim()
  if (!text || streaming.value) return

  banner.value = ''
  messages.value.push({ id: uid(), role: 'user', content: text })
  const assistantMsg = { id: uid(), role: 'assistant', content: '', pending: true }
  messages.value.push(assistantMsg)
  draft.value = ''
  resizeTextarea()
  streaming.value = true
  scrollToBottom()

  const body = {
    messages: [{ role: 'user', content: text }],
    stream: true,
  }
  if (DEFAULT_MODEL) body.model = DEFAULT_MODEL

  abortCtrl = new AbortController()
  let completed = false

  try {
    const resp = await fetch(chatUrl(), {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify(body),
      signal: abortCtrl.signal,
    })

    if (!resp.ok) {
      let detail = `HTTP ${resp.status}`
      try {
        const err = await resp.json()
        if (err.detail) detail = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail)
      } catch {
        /* ignore */
      }
      throw new Error(detail)
    }

    if (!resp.body) throw new Error('响应不支持流式读取')
    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      let idx
      while ((idx = buffer.indexOf('\n\n')) !== -1) {
        const block = buffer.slice(0, idx)
        buffer = buffer.slice(idx + 2)
        const parsed = parseSseBlock(block)
        if (!parsed) continue
        let data = null
        try {
          data = JSON.parse(parsed.data)
        } catch {
          data = { raw: parsed.data }
        }
        switch (parsed.event) {
          case 'meta': {
            currentSessionId.value = data.session_id || currentSessionId.value
            localStorage.setItem(CURRENT_SESSION_KEY, currentSessionId.value)
            upsertSession(currentSessionId.value, messages.value.find((m) => m.role === 'user')?.content || '')
            break
          }
          case 'delta':
            assistantMsg.content += data.content || ''
            scrollToBottom()
            break
          case 'done':
            completed = true
            break
          case 'error':
            throw new Error(data.message || '服务端返回错误')
          default:
            break
        }
      }
    }

    if (!completed && !assistantMsg.content) throw new Error('模型未返回内容')
    if (assistantMsg.content) upsertSession(currentSessionId.value, '')
  } catch (e) {
    if (e.name !== 'AbortError') {
      // 401 = 令牌过期：自动续期，成功后提示重发
      if (String(e.message || '').includes('401')) {
        const refreshed = await auth.ensureSession()
        if (refreshed) {
          banner.value = '登录令牌已自动续期，请重新发送刚才的消息。'
          if (!assistantMsg.content) assistantMsg.content = ''
          messages.value = messages.value.filter((m) => m !== assistantMsg)
        } else {
          router.replace({ name: 'chat-login' })
        }
      } else {
        banner.value = `请求失败：${e.message}`
        if (!assistantMsg.content) {
          assistantMsg.content = `> ⚠️ ${e.message}`
        }
      }
    }
  } finally {
    assistantMsg.pending = false
    streaming.value = false
    abortCtrl = null
    scrollToBottom()
  }
}

function stop() {
  if (abortCtrl) abortCtrl.abort()
}

/* ------------------------------- 会话管理 ------------------------------- */
async function loadSessions() {
  try {
    const resp = await fetch(`${API_BASE.replace(/\/+$/, '')}/v1/sessions`, {
      headers: authHeaders(),
    })
    if (!resp.ok) return
    const list = await resp.json()
    sessions.value = list.map((s) => ({
      id: s.id,
      title: s.title,
      updatedAt: Math.round((s.updated_at || 0) * 1000),
    }))
    persistSessionList()
  } catch {
    /* 服务不可用时保留本地会话列表 */
  }
}

async function selectSession(s) {
  if (streaming.value) return
  try {
    const resp = await fetch(
      `${API_BASE.replace(/\/+$/, '')}/v1/sessions/${encodeURIComponent(s.id)}`,
      { headers: authHeaders() },
    )
    if (!resp.ok) {
      if (resp.status === 404) {
        sessions.value = sessions.value.filter((x) => x.id !== s.id)
        persistSessionList()
      }
      throw new Error(`HTTP ${resp.status}`)
    }
    const detail = await resp.json()
    messages.value = (detail.messages || []).map((m) => ({
      id: uid(),
      role: m.role,
      content: m.content,
      pending: false,
    }))
    currentSessionId.value = s.id
    localStorage.setItem(CURRENT_SESSION_KEY, s.id)
    scrollToBottom()
  } catch (e) {
    banner.value = `加载会话失败：${e.message}`
  }
}

async function deleteSession(s) {
  try {
    await fetch(`${API_BASE.replace(/\/+$/, '')}/v1/sessions/${encodeURIComponent(s.id)}`, {
      method: 'DELETE',
      headers: authHeaders(),
    })
  } catch {
    /* 忽略删除失败，本地仍移除 */
  }
  sessions.value = sessions.value.filter((x) => x.id !== s.id)
  persistSessionList()
  if (currentSessionId.value === s.id) newChat()
}

function newChat() {
  if (streaming.value) stop()
  messages.value = []
  currentSessionId.value = ''
  localStorage.removeItem(CURRENT_SESSION_KEY)
  banner.value = ''
}

/* ------------------------------- 健康检查 ------------------------------- */
async function checkHealth() {
  status.value = 'checking'
  try {
    let resp = await fetch(`${API_BASE.replace(/\/+$/, '')}/v1/health`, {
      headers: authHeaders(),
    })
    if (resp.status === 401) {
      // access 令牌过期：自动用 refresh 换新后重试一次
      const refreshed = await auth.ensureSession()
      if (refreshed) {
        resp = await fetch(`${API_BASE.replace(/\/+$/, '')}/v1/health`, {
          headers: authHeaders(),
        })
      }
    }
    if (resp.status === 401) {
      status.value = 'offline'
      router.replace({ name: 'chat-login' })
      return
    }
    status.value = resp.ok ? 'online' : 'offline'
  } catch {
    status.value = 'offline'
  }
}

/* -------------------------------- 其他操作 -------------------------------- */
async function copyMessage(m) {
  try {
    await navigator.clipboard.writeText(m.content)
    toast('已复制到剪贴板')
  } catch {
    toast('复制失败')
  }
}

function resizeTextarea() {
  nextTick(() => {
    const el = textareaEl.value
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`
  })
}

function onComposerKeydown(e) {
  // 输入法组合期间（如中文拼音）不触发发送
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault()
    send()
  }
}

async function onLogout() {
  await auth.logout()
  router.push({ name: 'chat-login' })
}

/* -------------------------------- 生命周期 -------------------------------- */
watch(
  () => streaming.value,
  () => scrollToBottom(),
)

onMounted(async () => {
  // 对话平台需登录：未登录跳转专属登录页（账号与管理平台互通）
  if (!auth.accessToken) {
    router.replace({ name: 'chat-login' })
    return
  }
  // access 令牌可能已过期：用 refresh 自动续期（失败则回登录页）
  const fresh = await auth.ensureSession()
  if (!fresh) {
    router.replace({ name: 'chat-login' })
    return
  }
  try {
    const list = JSON.parse(localStorage.getItem(SESSION_LIST_KEY) || '[]')
    if (Array.isArray(list)) sessions.value = list
  } catch {
    /* ignore */
  }
  checkHealth()
  loadSessions()
})
</script>

<template>
  <div class="app">
    <!-- ============================ 侧边栏 ============================ -->
    <aside class="sidebar" :class="{ closed: !sidebarOpen }">
      <div class="sidebar-head">
        <button class="new-chat" @click="newChat">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <path d="M12 5v14M5 12h14" />
          </svg>
          <span>新对话</span>
        </button>
      </div>

      <nav class="session-list">
        <button
          v-for="s in sessions"
          :key="s.id"
          class="session-item"
          :class="{ active: s.id === currentSessionId && messages.length > 0 }"
          :title="s.title"
          @click="selectSession(s)"
        >
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
          <span class="session-title">{{ s.title }}</span>
          <span class="session-time">{{ fmtTime(s.updatedAt) }}</span>
          <span class="session-del" title="删除会话" @click.stop="deleteSession(s)">
            <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </span>
        </button>
        <p v-if="sessions.length === 0" class="session-empty">暂无历史会话</p>
      </nav>

      <div class="sidebar-foot">
        <div v-if="auth.user" class="user-row">
          <span class="user-avatar">{{ (auth.user.username || '?')[0].toUpperCase() }}</span>
          <div class="user-meta">
            <span class="user-name">{{ auth.user.username }}</span>
            <span class="user-role">{{ auth.user.role_name }}</span>
          </div>
          <button class="logout-btn" title="退出登录" @click="onLogout">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" />
            </svg>
          </button>
        </div>
        <div class="status-row">
          <span class="dot" :class="status"></span>
          <span class="status-text">
            {{ status === 'online' ? '服务正常' : status === 'checking' ? '连接中…' : '未连接' }}
          </span>
        </div>
      </div>
    </aside>

    <!-- ============================ 主区域 ============================ -->
    <main class="main">
      <header class="topbar">
        <button class="icon-btn" title="收起/展开侧边栏" @click="sidebarOpen = !sidebarOpen">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <path d="M3 6h18M3 12h18M3 18h18" />
          </svg>
        </button>
        <div class="brand">
          <span class="brand-logo">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
              <path d="M12 2l2.2 6.2L20 10l-5.8 1.8L12 18l-2.2-6.2L4 10l5.8-1.8L12 2z" />
            </svg>
          </span>
          <span class="brand-name">Dialogue</span>
        </div>
        <div class="topbar-right">
          <span class="model-chip">{{ modelLabel }}</span>
        </div>
      </header>

      <div v-if="banner" class="banner">
        <span>{{ banner }}</span>
        <button class="banner-close" @click="banner = ''">×</button>
      </div>

      <section ref="msgScroll" class="messages">
        <!-- 消息列表 -->
        <div v-for="m in messages" :key="m.id" class="msg-row" :class="m.role">
          <div class="avatar" :class="m.role">
            <svg v-if="m.role === 'assistant'" viewBox="0 0 24 24" width="15" height="15" fill="currentColor">
              <path d="M12 2l2.2 6.2L20 10l-5.8 1.8L12 18l-2.2-6.2L4 10l5.8-1.8L12 2z" />
            </svg>
            <span v-else>我</span>
          </div>
          <div class="msg-body">
            <div class="msg-content">
              <div v-if="m.role === 'user'" class="user-text">{{ m.content }}</div>
              <div v-else class="md" v-html="renderMd(m.content)"></div>
              <span v-if="m.pending && !m.content" class="typing">
                <i></i><i></i><i></i>
              </span>
              <span v-else-if="m.pending" class="cursor"></span>
            </div>
            <div class="msg-actions">
              <button class="action-btn" title="复制" @click="copyMessage(m)">
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <rect x="9" y="9" width="13" height="13" rx="2" />
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- 输入区 -->
      <footer class="composer">
        <div class="composer-box">
          <textarea
            ref="textareaEl"
            v-model="draft"
            rows="1"
            placeholder="输入消息，Enter 发送，Shift + Enter 换行"
            @keydown="onComposerKeydown"
            @input="resizeTextarea"
          ></textarea>
          <div class="composer-actions">
            <button v-if="streaming" class="send-btn stop" title="停止生成" @click="stop">
              <span class="stop-ico"></span>
              停止
            </button>
            <button v-else class="send-btn" :disabled="!canSend" title="发送" @click="send">
              <svg viewBox="0 0 24 24" width="15" height="15" fill="currentColor">
                <path d="M3.4 20.4l17.6-7.2c1-.4 1-1.8 0-2.2L3.4 3.6c-.9-.4-1.9.4-1.7 1.4L3.5 11c.1.6.5 1 1.1 1.1L14 14l-9.4 1.9c-.6.1-1 .5-1.1 1.1L1.7 19c-.2 1 .8 1.8 1.7 1.4z" />
              </svg>
            </button>
          </div>
        </div>
      </footer>
    </main>

    <!-- Toast -->
    <transition name="fade">
      <div v-if="toastMsg" class="toast">{{ toastMsg }}</div>
    </transition>
  </div>
</template>

<style scoped>
.app {
  display: flex;
  height: 100%;
  background: var(--bg);
  overflow: hidden;
}

/* ------------------------------ 侧边栏 ------------------------------ */
.sidebar {
  width: var(--sidebar-w);
  min-width: var(--sidebar-w);
  display: flex;
  flex-direction: column;
  background: var(--bg-soft);
  border-right: 1px solid var(--border-soft);
  transition: margin 0.25s ease;
}

.sidebar.closed {
  margin-left: calc(-1 * var(--sidebar-w));
}

.sidebar-head {
  padding: 14px 12px 10px;
}

.new-chat {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 9px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--panel);
  color: var(--text);
  font-size: 14px;
  transition:
    background 0.15s,
    border-color 0.15s;
}

.new-chat:hover {
  background: var(--panel-2);
  border-color: #2e2e36;
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 10px;
}

.session-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 9px 10px;
  margin-bottom: 2px;
  border-radius: var(--radius-sm);
  color: var(--text-2);
  font-size: 13.5px;
  text-align: left;
  transition: background 0.15s;
}

.session-item:hover {
  background: var(--panel);
  color: var(--text);
}

.session-item.active {
  background: var(--panel-2);
  color: var(--text);
}

.session-item svg {
  flex: none;
  opacity: 0.6;
}

.session-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-time {
  flex: none;
  font-size: 11px;
  color: var(--text-3);
}

.session-del {
  display: none;
  color: var(--text-3);
}

.session-item:hover .session-del {
  display: inline-flex;
}

.session-del:hover {
  color: var(--danger);
}

.session-empty {
  padding: 20px 12px;
  text-align: center;
  font-size: 12.5px;
  color: var(--text-3);
}

.sidebar-foot {
  padding: 12px;
  border-top: 1px solid var(--border-soft);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.status-row {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12.5px;
  color: var(--text-2);
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-3);
}

.dot.online {
  background: var(--ok);
  box-shadow: 0 0 6px rgba(52, 211, 153, 0.5);
}

.dot.checking {
  background: #f5b544;
}

.dot.offline {
  background: var(--danger);
}

.user-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-sm);
  background: var(--panel);
}

.user-avatar {
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 9px;
  background: var(--accent-soft);
  color: var(--accent);
  font-size: 13px;
  font-weight: 600;
}

.user-meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  line-height: 1.35;
}

.user-name {
  font-size: 13px;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-role {
  font-size: 11px;
  color: var(--text-3);
}

.logout-btn {
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 7px;
  color: var(--text-3);
  transition:
    background 0.15s,
    color 0.15s;
}

.logout-btn:hover {
  background: rgba(255, 92, 92, 0.12);
  color: var(--danger);
}

/* ------------------------------ 顶栏 ------------------------------ */
.main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: var(--bg);
}

.topbar {
  height: 54px;
  flex: none;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 18px;
  border-bottom: 1px solid var(--border-soft);
}

.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: var(--radius-sm);
  color: var(--text-2);
  font-size: 18px;
  transition: background 0.15s;
}

.icon-btn:hover {
  background: var(--panel);
  color: var(--text);
}

.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 15px;
  letter-spacing: 0.2px;
}

.brand-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 7px;
  background: var(--accent-soft);
  color: var(--accent);
}

.topbar-right {
  margin-left: auto;
}

.model-chip {
  padding: 3px 10px;
  border: 1px solid var(--border);
  border-radius: 999px;
  font-size: 12px;
  color: var(--text-2);
  background: var(--panel);
}

/* ------------------------------ 错误横幅 ------------------------------ */
.banner {
  flex: none;
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 10px auto 0;
  width: min(92%, var(--max-chat-w));
  padding: 9px 14px;
  border: 1px solid rgba(255, 92, 92, 0.35);
  border-radius: var(--radius-sm);
  background: rgba(255, 92, 92, 0.08);
  color: #ffb3b3;
  font-size: 13px;
}

.banner span {
  flex: 1;
}

.banner-close {
  color: #ffb3b3;
  font-size: 16px;
}

/* ------------------------------ 消息区 ------------------------------ */
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 22px 22px 10px;
  scroll-behavior: smooth;
}

/* 消息行铺满整宽：助手靠左、用户靠右 */
.msg-row {
  display: flex;
  gap: 12px;
  width: 100%;
  margin: 0 0 22px;
}

.msg-row.user {
  flex-direction: row-reverse;
}

.avatar {
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 9px;
  font-size: 12px;
}

.avatar.assistant {
  background: var(--accent-soft);
  color: var(--accent);
}

.avatar.user {
  background: var(--panel-2);
  border: 1px solid var(--border);
  color: var(--text-2);
}

.msg-body {
  min-width: 0;
  /* 内容仍有最大宽度上限，保证长文本可读性 */
  max-width: min(calc(100% - 42px), 780px);
}

.msg-row.user .msg-body {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.msg-content {
  position: relative;
}

.user-text {
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: 14px 14px 4px 14px;
  background: var(--panel);
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 14.5px;
}

.msg-row.assistant .msg-content {
  padding-top: 4px;
  font-size: 14.5px;
}

.msg-actions {
  margin-top: 6px;
  opacity: 0;
  transition: opacity 0.15s;
}

.msg-row:hover .msg-actions {
  opacity: 1;
}

.action-btn {
  display: inline-flex;
  padding: 4px;
  border-radius: 6px;
  color: var(--text-3);
}

.action-btn:hover {
  color: var(--text);
  background: var(--panel);
}

/* 流式输出光标 */
.cursor {
  display: inline-block;
  width: 8px;
  height: 16px;
  margin-left: 2px;
  vertical-align: -2px;
  background: var(--accent);
  border-radius: 1px;
  animation: blink 0.9s steps(1) infinite;
}

@keyframes blink {
  50% {
    opacity: 0;
  }
}

/* 等待首字时的三点动画 */
.typing {
  display: inline-flex;
  gap: 4px;
  padding: 8px 0;
}

.typing i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-3);
  animation: bounce 1.2s infinite ease-in-out;
}

.typing i:nth-child(2) {
  animation-delay: 0.15s;
}

.typing i:nth-child(3) {
  animation-delay: 0.3s;
}

@keyframes bounce {
  0%,
  60%,
  100% {
    transform: translateY(0);
    opacity: 0.5;
  }
  30% {
    transform: translateY(-4px);
    opacity: 1;
  }
}

/* ------------------------------ 输入区 ------------------------------ */
.composer {
  flex: none;
  padding: 8px 18px 16px;
}

.composer-box {
  max-width: var(--max-chat-w);
  margin: 0 auto;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: var(--panel);
  padding: 10px 12px 8px;
  transition: border-color 0.15s;
}

.composer-box:focus-within {
  border-color: #3a3a45;
}

.composer textarea {
  display: block;
  width: 100%;
  resize: none;
  border: none;
  outline: none;
  background: transparent;
  font-size: 14.5px;
  line-height: 1.55;
  max-height: 200px;
  padding: 2px 4px;
}

.composer textarea::placeholder {
  color: var(--text-3);
}

.composer-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 6px;
}

.send-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: auto;
  padding: 7px 12px;
  border-radius: 9px;
  background: #1e40af; /* 深蓝 */
  color: #fff;
  font-size: 13.5px;
  transition:
    background 0.15s,
    opacity 0.15s;
}

.send-btn:hover:not(:disabled) {
  background: #2a55cc;
}

.send-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.send-btn.stop {
  background: #1e40af; /* 深蓝 */
  border: none;
  color: #fff;
}

.send-btn.stop:hover {
  background: #2a55cc;
}

.stop-ico {
  width: 9px;
  height: 9px;
  border-radius: 2px;
  background: currentColor;
}

/* ------------------------------ Toast ------------------------------ */
.toast {
  position: fixed;
  left: 50%;
  bottom: 110px;
  transform: translateX(-50%);
  z-index: 60;
  padding: 8px 16px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--panel-2);
  color: var(--text);
  font-size: 13px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
