<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import http from '@/api'

const router = useRouter()

const step = ref(1) // 1 发送验证码 / 2 输入验证码 / 3 设置新密码
const loading = ref(false)
const form = reactive({ username: '', code: '', password: '', confirm: '' })
const resetToken = ref('')
const maskedEmail = ref('')
const debugCode = ref('')
const sent = ref(false)

async function onSendCode() {
  if (!form.username.trim()) {
    ElMessage.warning('请输入用户名')
    return
  }
  loading.value = true
  try {
    const data = await http.post('/api/auth/reset/request', { username: form.username.trim() })
    if (data.debug_code) {
      // 开发模式（未配置 SMTP）：验证码直接显示，生产环境不会返回
      debugCode.value = data.debug_code
      ElMessage.info(`开发模式验证码：${data.debug_code}`)
    }
    sent.value = true
    maskedEmail.value = data.masked_email || ''
    step.value = 2
  } finally {
    loading.value = false
  }
}

async function onVerifyCode() {
  if (!form.code.trim()) {
    ElMessage.warning('请输入验证码')
    return
  }
  loading.value = true
  try {
    const data = await http.post('/api/auth/reset/verify', {
      username: form.username.trim(),
      code: form.code.trim(),
    })
    resetToken.value = data.reset_token
    step.value = 3
  } finally {
    loading.value = false
  }
}

async function onSubmitNewPassword() {
  if (form.password.length < 8) {
    ElMessage.warning('新密码至少 8 位')
    return
  }
  if (form.password !== form.confirm) {
    ElMessage.warning('两次输入的密码不一致')
    return
  }
  loading.value = true
  try {
    await http.post('/api/auth/reset/confirm', {
      reset_token: resetToken.value,
      new_password: form.password,
    })
    ElMessage.success('密码已重置，请使用新密码登录')
    router.push('/login')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="reset-page">
    <div class="reset-card">
      <div class="head">
        <span class="logo">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
            <path d="M12 2l2.2 6.2L20 10l-5.8 1.8L12 18l-2.2-6.2L4 10l5.8-1.8L12 2z" />
          </svg>
        </span>
        <div>
          <h1>找回密码</h1>
          <p>通过绑定邮箱的验证码重置登录密码</p>
        </div>
      </div>

      <el-steps :active="step - 1" align-center finish-status="success" class="steps">
        <el-step title="验证身份" />
        <el-step title="输入验证码" />
        <el-step title="设置新密码" />
      </el-steps>

      <!-- 步骤 1：输入用户名 -->
      <el-form v-if="step === 1" label-position="top" @submit.prevent="onSendCode">
        <el-form-item label="用户名">
          <el-input v-model="form.username" size="large" placeholder="请输入用户名" autocomplete="username" />
        </el-form-item>
        <el-button type="primary" size="large" class="full" :loading="loading" @click="onSendCode">
          发送验证码
        </el-button>
      </el-form>

      <!-- 步骤 2：输入验证码 -->
      <el-form v-else-if="step === 2" label-position="top" @submit.prevent="onVerifyCode">
        <p v-if="maskedEmail" class="hint-line">验证码已发送至：{{ maskedEmail }}</p>
        <p v-else class="hint-line">验证码已发送至绑定邮箱（10 分钟内有效）</p>
        <el-form-item label="邮箱验证码">
          <el-input
            v-model="form.code"
            size="large"
            maxlength="6"
            placeholder="6 位数字验证码"
            @keyup.enter="onVerifyCode"
          />
        </el-form-item>
        <el-button type="primary" size="large" class="full" :loading="loading" @click="onVerifyCode">
          验证
        </el-button>
        <el-button text class="full" @click="step = 1">← 返回上一步</el-button>
      </el-form>

      <!-- 步骤 3：设置新密码 -->
      <el-form v-else label-position="top" @submit.prevent="onSubmitNewPassword">
        <el-form-item label="新密码">
          <el-input v-model="form.password" type="password" size="large" show-password placeholder="至少 8 位" />
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input
            v-model="form.confirm"
            type="password"
            size="large"
            show-password
            placeholder="再次输入新密码"
            @keyup.enter="onSubmitNewPassword"
          />
        </el-form-item>
        <el-button type="primary" size="large" class="full" :loading="loading" @click="onSubmitNewPassword">
          重置密码
        </el-button>
      </el-form>

      <router-link class="back-link" to="/login">← 返回登录</router-link>
    </div>
  </div>
</template>

<style scoped>
.reset-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg, #0a0a0b);
}

.reset-card {
  width: 420px;
  max-width: calc(100vw - 40px);
  padding: 32px 30px 26px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 14px;
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.08),
    rgba(255, 255, 255, 0.02) 50%,
    rgba(255, 255, 255, 0.05)
  );
  backdrop-filter: blur(24px) saturate(1.5);
  -webkit-backdrop-filter: blur(24px) saturate(1.5);
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.5);
}

.head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.logo {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 11px;
  background: rgba(142, 142, 152, 0.16);
  color: #8e8e98;
}

.head h1 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #ececef;
}

.head p {
  margin: 2px 0 0;
  font-size: 12px;
  color: #67676f;
}

.steps {
  margin-bottom: 22px;
}

.hint-line {
  margin: 0 0 12px;
  font-size: 12.5px;
  color: #a2a2ab;
}

.full {
  width: 100%;
  margin-top: 6px;
}

.back-link {
  display: block;
  margin-top: 18px;
  text-align: center;
  font-size: 13px;
  color: #8e8e98;
  text-decoration: none;
  transition: color 0.15s;
}

.back-link:hover {
  color: #ececef;
}
</style>
