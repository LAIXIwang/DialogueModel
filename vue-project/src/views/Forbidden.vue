<script setup>
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

async function onLogout() {
  await auth.logout()
  router.push('/chat-login')
}
</script>

<template>
  <div class="forbidden-page">
    <div class="forbidden-card">
      <div class="icon">
        <svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="11" width="18" height="11" rx="2" />
          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
        </svg>
      </div>
      <h1>无权限访问</h1>
      <p>当前账号（{{ auth.user?.role_name || '—' }}）没有后台管理权限</p>
      <div class="actions">
        <el-button @click="router.push('/')">返回对话平台</el-button>
        <el-button type="primary" @click="onLogout">切换账号</el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.forbidden-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg, #0a0a0b);
}

.forbidden-card {
  width: 380px;
  max-width: calc(100vw - 40px);
  padding: 40px 32px 32px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 14px;
  text-align: center;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0.02) 50%, rgba(255, 255, 255, 0.05));
  backdrop-filter: blur(24px) saturate(1.5);
  -webkit-backdrop-filter: blur(24px) saturate(1.5);
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.5);
}

.icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border-radius: 16px;
  background: rgba(255, 92, 92, 0.12);
  color: var(--danger, #ff5c5c);
  margin-bottom: 14px;
}

h1 {
  margin: 0 0 8px;
  font-size: 19px;
  font-weight: 600;
  color: #ececef;
}

p {
  margin: 0 0 22px;
  font-size: 13px;
  color: #a2a2ab;
}

.actions {
  display: flex;
  justify-content: center;
  gap: 10px;
}
</style>
