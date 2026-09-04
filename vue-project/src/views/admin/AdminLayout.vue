<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ChatDotRound,
  DataAnalysis,
  Document,
  Files,
  Lock,
  Monitor,
  Setting,
  SwitchButton,
  User,
  UserFilled,
} from '@element-plus/icons-vue'

import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const menus = computed(() => {
  const all = [
    { path: '/admin/users', title: '用户管理', icon: User, perm: 'user:list' },
    { path: '/admin/groups', title: '分组管理', icon: Files, perm: 'group:list' },
    { path: '/admin/roles', title: '角色权限', icon: Lock, perm: 'role:list' },
    { path: '/admin/conversations', title: '会话管理', icon: ChatDotRound, perm: 'conversation:list' },
    { path: '/admin/stats', title: '配额统计', icon: DataAnalysis, perm: 'stats:read' },
    { path: '/admin/model', title: '模型接入', icon: Setting, perm: 'model:read' },
    { path: '/admin/logs', title: '审计日志', icon: Document, perm: 'log:read' },
  ]
  return all.filter((m) => auth.hasPerm(m.perm))
})

async function onLogout() {
  try {
    await ElMessageBox.confirm('确定退出登录吗？', '提示', { type: 'warning' })
  } catch {
    return
  }
  await auth.logout()
  ElMessage.success('已退出登录')
  router.push('/login')
}
</script>

<template>
  <div class="admin-shell">
    <aside class="admin-aside">
      <div class="admin-brand">
        <span class="brand-ico">
          <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
            <path d="M12 2l2.2 6.2L20 10l-5.8 1.8L12 18l-2.2-6.2L4 10l5.8-1.8L12 2z" />
          </svg>
        </span>
        <div class="brand-text">
          <b>Dialogue</b>
          <span>管理平台</span>
        </div>
      </div>

      <el-menu
        :default-active="route.path"
        class="admin-menu"
        router
      >
        <el-menu-item v-for="m in menus" :key="m.path" :index="m.path">
          <el-icon><component :is="m.icon" /></el-icon>
          <span>{{ m.title }}</span>
        </el-menu-item>
      </el-menu>

      <div class="admin-aside-foot">
        <el-button text class="back-chat" :icon="Monitor" @click="router.push('/')">返回对话平台</el-button>
      </div>
    </aside>

    <div class="admin-main">
      <header class="admin-topbar">
        <span class="page-name">{{ route.meta.title || '' }}</span>
        <div class="topbar-right">
          <span class="role-tag">{{ auth.roleName }}</span>
          <el-dropdown>
            <span class="user-chip">
              <el-icon><UserFilled /></el-icon>
              {{ auth.user?.username || '…' }}
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item :icon="SwitchButton" @click="onLogout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <main class="admin-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<style scoped>
.admin-shell {
  display: flex;
  height: 100vh;
  background: var(--bg, #0a0a0b);
  overflow: hidden;
}

.admin-aside {
  width: 216px;
  flex: none;
  display: flex;
  flex-direction: column;
  background: var(--bg-soft, #0e0e11);
  border-right: 1px solid var(--border, #2b2b34);
}

.admin-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 18px 16px 14px;
}

.brand-ico {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: rgba(142, 142, 152, 0.16);
  color: #8e8e98;
}

.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.3;
}

.brand-text b {
  font-size: 14px;
  color: #ececef;
}

.brand-text span {
  font-size: 11px;
  color: #67676f;
}

.admin-menu {
  flex: 1;
  border-right: none;
  background: transparent;
  padding: 4px 8px;
}

.admin-menu :deep(.el-menu-item) {
  height: 42px;
  margin-bottom: 2px;
  border-radius: 8px;
  color: #a2a2ab;
}

.admin-menu :deep(.el-menu-item:hover) {
  background: #131317;
  color: #ececef;
}

.admin-menu :deep(.el-menu-item.is-active) {
  background: rgba(30, 64, 175, 0.22);
  color: #7d9bff;
}

.admin-aside-foot {
  padding: 12px;
  border-top: 1px solid var(--border, #2b2b34);
}

.back-chat {
  width: 100%;
  color: #a2a2ab;
}

.admin-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.admin-topbar {
  height: 54px;
  flex: none;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 20px;
  border-bottom: 1px solid var(--border, #2b2b34);
  background: var(--bg-soft, #0e0e11);
}

.page-name {
  font-size: 15px;
  font-weight: 600;
  color: #ececef;
}

.topbar-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 12px;
}

.role-tag {
  padding: 2px 10px;
  border: 1px solid #232329;
  border-radius: 999px;
  font-size: 12px;
  color: #a2a2ab;
}

.user-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #c8c8d0;
  cursor: pointer;
  outline: none;
}

.admin-content {
  flex: 1;
  overflow-y: auto;
}
</style>
