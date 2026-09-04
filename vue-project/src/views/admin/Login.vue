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
    ElMessage.success('登录成功')
    router.push(route.query.redirect || '/admin')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-head">
        <span class="login-logo">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
            <path d="M12 2l2.2 6.2L20 10l-5.8 1.8L12 18l-2.2-6.2L4 10l5.8-1.8L12 2z" />
          </svg>
        </span>
        <div>
          <h1>Dialogue 管理平台</h1>
          <p>AI 对话用户管理系统</p>
        </div>
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
        <el-button type="primary" size="large" class="login-btn" :loading="loading" @click="onSubmit">
          登 录
        </el-button>
      </el-form>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg, #0a0a0b);
}

.login-card {
  width: 380px;
  max-width: calc(100vw - 40px);
  padding: 34px 32px 26px;
  border: 1px solid var(--border, #232329);
  border-radius: 14px;
  background: var(--bg-soft, #0e0e11);
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.5);
}

.login-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 26px;
}

.login-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 11px;
  background: rgba(142, 142, 152, 0.16);
  color: #8e8e98;
}

.login-head h1 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #ececef;
}

.login-head p {
  margin: 2px 0 0;
  font-size: 12px;
  color: #67676f;
}

.login-btn {
  width: 100%;
  margin-top: 6px;
}
</style>
