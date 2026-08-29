import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import http from '@/api'

export const useAuthStore = defineStore('admin-auth', () => {
  const accessToken = ref(localStorage.getItem('dialogue.admin.access') || '')
  const refreshToken = ref(localStorage.getItem('dialogue.admin.refresh') || '')
  const user = ref(JSON.parse(localStorage.getItem('dialogue.admin.user') || 'null'))

  const permissions = computed(() => user.value?.permissions || [])
  const roleName = computed(() => user.value?.role_name || '')

  function hasPerm(code) {
    if (!user.value) return false
    if (user.value.role_code === 'super_admin') return true
    return permissions.value.includes(code)
  }

  async function login(username, password) {
    const data = await http.post('/api/auth/login', { username, password })
    accessToken.value = data.access_token
    refreshToken.value = data.refresh_token
    user.value = data.user
    localStorage.setItem('dialogue.admin.access', data.access_token)
    localStorage.setItem('dialogue.admin.refresh', data.refresh_token)
    localStorage.setItem('dialogue.admin.user', JSON.stringify(data.user))
    return data
  }

  async function fetchMe() {
    const data = await http.get('/api/auth/me')
    user.value = data
    localStorage.setItem('dialogue.admin.user', JSON.stringify(data))
    return data
  }

  /** 确保令牌有效：access 过期时 http 拦截器会自动用 refresh 换新；失败返回 false */
  async function ensureSession() {
    try {
      await fetchMe()
      return true
    } catch {
      return false
    }
  }

  async function logout() {
    try {
      await http.post('/api/auth/logout', { refresh_token: refreshToken.value })
    } catch {
      /* 忽略登出接口错误 */
    }
    accessToken.value = ''
    refreshToken.value = ''
    user.value = null
    localStorage.removeItem('dialogue.admin.access')
    localStorage.removeItem('dialogue.admin.refresh')
    localStorage.removeItem('dialogue.admin.user')
  }

  return {
    accessToken,
    refreshToken,
    user,
    permissions,
    roleName,
    hasPerm,
    login,
    fetchMe,
    ensureSession,
    logout,
  }
})
