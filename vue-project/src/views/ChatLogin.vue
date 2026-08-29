<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const form = reactive({ username: '', password: '' })
const loading = ref(false)

async function onSubmit() {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    ElMessage.success(`欢迎回来，${auth.user?.username}`)
    router.push(route.query.redirect || '/')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="chat-login">
    <div class="login-box">
      <div class="login-brand">
        <span class="logo">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
            <path d="M12 2l2.2 6.2L20 10l-5.8 1.8L12 18l-2.2-6.2L4 10l5.8-1.8L12 2z" />
          </svg>
        </span>
        <h1>Dialogue</h1>
        <p>AI 对话平台</p>
      </div>

      <el-form label-position="top" @submit.prevent="onSubmit">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="请输入用户名" size="large" autocomplete="username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            size="large"
            show-password
            autocomplete="current-password"
            @keyup.enter="onSubmit"
          />
        </el-form-item>
        <el-button type="primary" size="large" class="submit" :loading="loading" @click="onSubmit">
          进入对话
        </el-button>
      </el-form>

      <p class="hint">账号与管理平台互通 · 对话记录与配额记入你的账户</p>
      <router-link class="admin-link" to="/login">管理平台入口 →</router-link>
    </div>
  </div>
</template>

<style scoped>
.chat-login {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg, #0a0a0b);
}

.login-box {
  width: 380px;
  max-width: calc(100vw - 40px);
  padding: 34px 32px 26px;
  border: 1px solid var(--border, #232329);
  border-radius: 14px;
  background: var(--bg-soft, #0e0e11);
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.5);
}

.login-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 26px;
}

.logo {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: rgba(142, 142, 152, 0.16);
  color: #8e8e98;
}

.login-brand h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #ececef;
  letter-spacing: 0.3px;
}

.login-brand p {
  margin: 2px 0 0;
  font-size: 12px;
  color: #67676f;
}

.submit {
  width: 100%;
  margin-top: 6px;
}

.hint {
  margin: 18px 0 0;
  text-align: center;
  font-size: 12px;
  color: #67676f;
}

.admin-link {
  display: block;
  margin-top: 8px;
  text-align: center;
  font-size: 12.5px;
  color: #8e8e98;
  text-decoration: none;
}

.admin-link:hover {
  color: #ececef;
}
</style>
