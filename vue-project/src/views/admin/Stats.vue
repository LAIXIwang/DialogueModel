<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import http from '@/api'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const overview = ref(null)
const quotas = ref([])
const quotaLoading = ref(false)
const rlForm = reactive({ per_minute: 10 })
const quotaDialog = reactive({ visible: false, userId: null, username: '', dailyLimit: 0 })

async function loadOverview() {
  overview.value = await http.get('/api/stats/overview')
}

async function loadQuotas() {
  quotaLoading.value = true
  try {
    quotas.value = await http.get('/api/quotas')
  } finally {
    quotaLoading.value = false
  }
}

async function loadRateLimit() {
  const data = await http.get('/api/stats/rate-limit')
  rlForm.per_minute = data.per_minute
}

async function saveRateLimit() {
  await http.put('/api/stats/rate-limit', { per_minute: rlForm.per_minute })
  ElMessage.success('限流配置已生效')
  loadOverview()
}

function openQuota(row) {
  Object.assign(quotaDialog, {
    visible: true,
    userId: row.user_id,
    username: row.username,
    dailyLimit: row.daily_limit,
  })
}

async function saveQuota() {
  await http.put(`/api/quotas/${quotaDialog.userId}`, { daily_limit: quotaDialog.dailyLimit })
  ElMessage.success('配额已更新')
  quotaDialog.visible = false
  loadQuotas()
  loadOverview()
}

function fmtNum(n) {
  return Number(n || 0).toLocaleString()
}

onMounted(() => {
  loadOverview()
  loadQuotas()
  if (auth.hasPerm('quota:edit')) loadRateLimit()
})
</script>

<template>
  <div class="admin-page">
    <h2 class="page-title">配额统计</h2>

    <!-- 概览卡片 -->
    <div class="stat-cards">
      <div class="stat-card">
        <div class="stat-num">{{ fmtNum(overview?.total_users) }}</div>
        <div class="stat-label">用户总数（启用 {{ fmtNum(overview?.enabled_users) }} / 禁用 {{ fmtNum(overview?.disabled_users) }}）</div>
      </div>
      <div class="stat-card">
        <div class="stat-num">{{ fmtNum(overview?.today_calls) }}</div>
        <div class="stat-label">今日 AI 调用次数</div>
      </div>
      <div class="stat-card">
        <div class="stat-num">{{ fmtNum(overview?.today_tokens) }}</div>
        <div class="stat-label">今日消耗 Tokens</div>
      </div>
      <div class="stat-card">
        <div class="stat-num">{{ fmtNum(overview?.total_tokens) }}</div>
        <div class="stat-label">累计消耗 Tokens（共 {{ fmtNum(overview?.total_calls) }} 次调用）</div>
      </div>
      <div class="stat-card">
        <div class="stat-num">{{ fmtNum(overview?.online_sessions) }}</div>
        <div class="stat-label">在线会话（Redis 会话缓存）</div>
      </div>
    </div>

    <!-- 限流配置 -->
    <div v-if="auth.hasPerm('quota:edit')" class="panel">
      <div class="panel-head">
        <b>速率限制（RateLimit）</b>
        <span class="panel-hint">防止单用户短时间刷接口打崩大模型服务</span>
      </div>
      <div class="panel-body inline">
        <span>单用户每分钟最多</span>
        <el-input-number v-model="rlForm.per_minute" :min="1" :max="10000" style="width: 150px" />
        <span>次 AI 请求</span>
        <el-button type="primary" @click="saveRateLimit">保存</el-button>
        <span class="panel-hint">配置存于 Redis，BFF 每请求实时校验</span>
      </div>
    </div>

    <!-- 用户配额 -->
    <div class="panel">
      <div class="panel-head">
        <b>用户 AI 配额</b>
        <span class="panel-hint">每日 token 上限 · 剩余额度 · 累计消耗</span>
      </div>
      <el-table v-loading="quotaLoading" :data="quotas" border stripe style="width: 100%">
        <el-table-column prop="user_id" label="用户 ID" width="90" />
        <el-table-column prop="username" label="用户名" min-width="120" />
        <el-table-column label="每日上限" width="130" align="right">
          <template #default="{ row }">{{ fmtNum(row.daily_limit) }}</template>
        </el-table-column>
        <el-table-column label="今日已用" width="130" align="right">
          <template #default="{ row }">{{ fmtNum(row.used_today) }}</template>
        </el-table-column>
        <el-table-column label="剩余额度" width="130" align="right">
          <template #default="{ row }">
            <span :class="{ exhausted: row.remaining === 0 }">{{ fmtNum(row.remaining) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="累计消耗" width="140" align="right">
          <template #default="{ row }">{{ fmtNum(row.used_total) }}</template>
        </el-table-column>
        <el-table-column prop="last_date" label="统计日期" width="120" />
        <el-table-column label="操作" width="110" fixed="right">
          <template #default="{ row }">
            <el-button v-if="auth.hasPerm('quota:edit')" link type="primary" @click="openQuota(row)">
              调整配额
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="quotaDialog.visible" :title="`调整配额 · ${quotaDialog.username}`" width="380px">
      <div class="quota-form">
        <span>每日 token 上限</span>
        <el-input-number v-model="quotaDialog.dailyLimit" :min="0" :step="10000" style="width: 200px" />
      </div>
      <template #footer>
        <el-button @click="quotaDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="saveQuota">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.stat-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
  margin-bottom: 18px;
}

.stat-card {
  padding: 16px 18px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 10px;
  background: var(--el-bg-color);
}

.stat-num {
  font-size: 24px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.stat-label {
  margin-top: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.panel {
  margin-bottom: 18px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 10px;
  background: var(--el-bg-color);
  overflow: hidden;
}

.panel-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.panel-head b {
  font-size: 14px;
  color: var(--el-text-color-primary);
}

.panel-hint {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}

.panel-body {
  padding: 14px 16px;
}

.panel-body.inline {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: var(--el-text-color-regular);
}

.exhausted {
  color: var(--el-color-danger);
  font-weight: 600;
}

.quota-form {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  color: var(--el-text-color-regular);
}
</style>
