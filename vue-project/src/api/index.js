// Axios 实例：统一携带 Authorization 令牌 + 统一错误处理 + 刷新令牌
import axios from 'axios'
import { ElMessage } from 'element-plus'

import router from '@/router'

const http = axios.create({
  baseURL: '/admin-api',
  timeout: 30000,
})

// 请求拦截：统一携带令牌
http.interceptors.request.use((config) => {
  const token = localStorage.getItem('dialogue.admin.access')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 刷新令牌（401 时尝试一次，避免并发重复刷新）
let refreshing = null

async function tryRefresh() {
  const refresh = localStorage.getItem('dialogue.admin.refresh')
  if (!refresh) return null
  if (refreshing) return refreshing
  refreshing = axios
    .post('/admin-api/api/auth/refresh', { refresh_token: refresh })
    .then((r) => {
      const d = r.data?.data
      if (d?.access_token) {
        localStorage.setItem('dialogue.admin.access', d.access_token)
        localStorage.setItem('dialogue.admin.refresh', d.refresh_token || refresh)
        return d.access_token
      }
      return null
    })
    .catch(() => null)
    .finally(() => {
      refreshing = null
    })
  return refreshing
}

function clearAuth() {
  localStorage.removeItem('dialogue.admin.access')
  localStorage.removeItem('dialogue.admin.refresh')
  localStorage.removeItem('dialogue.admin.user')
}

// 响应拦截：统一解包 {code, message, data}
http.interceptors.response.use(
  (resp) => {
    const body = resp.data
    if (body && typeof body === 'object' && 'code' in body) {
      if (body.code === 0) return body.data
      ElMessage.error(body.message || '请求失败')
      return Promise.reject(new Error(body.message || '请求失败'))
    }
    return body
  },
  async (error) => {
    const { response, config } = error
    if (response?.status === 401 && !config._retried) {
      const newToken = await tryRefresh()
      if (newToken) {
        config._retried = true
        config.headers.Authorization = `Bearer ${newToken}`
        return http(config)
      }
      clearAuth()
      ElMessage.error('登录已失效，请重新登录')
      // 按当前所在平台跳到对应登录页
      const current = router.currentRoute.value
      const target = current.path.startsWith('/admin') ? 'login' : 'chat-login'
      router.push({ name: target, query: { redirect: current.fullPath } })
    } else if (response) {
      ElMessage.error(response.data?.message || `请求失败 (${response.status})`)
    } else {
      ElMessage.error('网络异常，请检查后端服务')
    }
    return Promise.reject(error)
  },
)

export default http
