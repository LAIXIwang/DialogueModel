import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import App from '@/App.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'chat',
      component: App,
      meta: { title: 'AI 对话', requiresChatAuth: true },
    },
    {
      path: '/chat-login',
      name: 'chat-login',
      component: () => import('@/views/ChatLogin.vue'),
      meta: { title: '登录', public: true },
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/admin/Login.vue'),
      meta: { title: '登录', public: true },
    },
    {
      path: '/reset-password',
      name: 'reset-password',
      component: () => import('@/views/ResetPassword.vue'),
      meta: { title: '找回密码', public: true },
    },
    {
      path: '/admin',
      component: () => import('@/views/admin/AdminLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        { path: '', redirect: '/admin/users' },
        {
          path: 'users',
          name: 'admin-users',
          component: () => import('@/views/admin/Users.vue'),
          meta: { title: '用户管理', requiresAuth: true },
        },
        {
          path: 'roles',
          name: 'admin-roles',
          component: () => import('@/views/admin/Roles.vue'),
          meta: { title: '角色权限', requiresAuth: true },
        },
        {
          path: 'groups',
          name: 'admin-groups',
          component: () => import('@/views/admin/Groups.vue'),
          meta: { title: '分组管理', requiresAuth: true },
        },
        {
          path: 'conversations',
          name: 'admin-conversations',
          component: () => import('@/views/admin/Conversations.vue'),
          meta: { title: '会话管理', requiresAuth: true },
        },
        {
          path: 'stats',
          name: 'admin-stats',
          component: () => import('@/views/admin/Stats.vue'),
          meta: { title: '配额统计', requiresAuth: true },
        },
        {
          path: 'model',
          name: 'admin-model',
          component: () => import('@/views/admin/ModelConfig.vue'),
          meta: { title: '模型接入', requiresAuth: true },
        },
        {
          path: 'logs',
          name: 'admin-logs',
          component: () => import('@/views/admin/Logs.vue'),
          meta: { title: '审计日志', requiresAuth: true },
        },
      ],
    },
  ],
})

// 全局路由守卫：对话平台与管理平台共用同一账号体系（同一 JWT）
router.beforeEach((to) => {
  const auth = useAuthStore()
  // 对话平台需登录
  if (to.meta.requiresChatAuth && !auth.accessToken) {
    return { name: 'chat-login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'chat-login' && auth.accessToken) {
    return { path: '/' }
  }
  // 管理平台需登录
  if (to.meta.requiresAuth && !auth.accessToken) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && auth.accessToken) {
    return { path: '/admin' }
  }
  document.title = (to.meta.title ? `${to.meta.title} · ` : '') + 'Dialogue'
  return true
})

export default router
