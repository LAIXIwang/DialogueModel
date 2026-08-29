<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Search } from '@element-plus/icons-vue'

import http from '@/api'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const loading = ref(false)
const list = ref([])
const total = ref(0)
const query = reactive({ page: 1, size: 10, keyword: '', user_id: null })
const users = ref([])

const detailDialog = reactive({ visible: false, row: null })

async function load() {
  loading.value = true
  try {
    const data = await http.get('/api/conversations', {
      params: {
        page: query.page,
        size: query.size,
        keyword: query.keyword || undefined,
        user_id: query.user_id ?? undefined,
      },
    })
    list.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function loadUsers() {
  if (!auth.hasPerm('user:list')) return
  const data = await http.get('/api/users', { params: { page: 1, size: 100 } })
  users.value = data.items
}

async function onDeleteRow(row) {
  try {
    await ElMessageBox.confirm('确定删除这条对话记录？', '提示', { type: 'warning' })
  } catch {
    return
  }
  await http.delete(`/api/conversations/${row.id}`)
  ElMessage.success('已删除')
  load()
}

async function onDeleteSession(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除会话 ${row.session_id.slice(0, 12)}… 下的全部对话记录？`,
      '警告',
      { type: 'error' },
    )
  } catch {
    return
  }
  await http.delete(`/api/conversations/session/${row.session_id}`)
  ElMessage.success('会话已删除')
  load()
}

function fmtTime(v) {
  return v ? String(v).replace('T', ' ').slice(0, 19) : '—'
}

onMounted(() => {
  load()
  loadUsers()
})
</script>

<template>
  <div class="admin-page">
    <h2 class="page-title">会话管理</h2>

    <div class="toolbar">
      <el-input
        v-model="query.keyword"
        placeholder="搜索提问 / 回答内容"
        style="width: 240px"
        clearable
        :prefix-icon="Search"
        @keyup.enter="query.page = 1; load()"
        @clear="query.page = 1; load()"
      />
      <el-select v-model="query.user_id" placeholder="按用户筛选" clearable filterable style="width: 180px" @change="query.page = 1; load()">
        <el-option v-for="u in users" :key="u.id" :label="u.username" :value="u.id" />
      </el-select>
      <el-button :icon="Search" @click="query.page = 1; load()">查询</el-button>
      <el-button :icon="Refresh" @click="load">刷新</el-button>
    </div>

    <el-table v-loading="loading" :data="list" border stripe style="width: 100%">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="username" label="用户" width="110" />
      <el-table-column prop="model" label="模型" width="130" />
      <el-table-column label="提问" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">{{ row.prompt }}</template>
      </el-table-column>
      <el-table-column label="回答" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">{{ row.answer }}</template>
      </el-table-column>
      <el-table-column prop="tokens" label="Tokens" width="90" align="right" />
      <el-table-column label="会话 ID" width="150">
        <template #default="{ row }">
          <span class="mono">{{ row.session_id.slice(0, 12) }}…</span>
        </template>
      </el-table-column>
      <el-table-column label="时间" width="165">
        <template #default="{ row }">{{ fmtTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="170" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="detailDialog.row = row; detailDialog.visible = true">详情</el-button>
          <el-button v-if="auth.hasPerm('conversation:delete')" link type="warning" @click="onDeleteSession(row)">
            删会话
          </el-button>
          <el-button v-if="auth.hasPerm('conversation:delete')" link type="danger" @click="onDeleteRow(row)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="admin-pager">
      <el-pagination
        v-model:current-page="query.page"
        v-model:page-size="query.size"
        :total="total"
        layout="total, sizes, prev, pager, next"
        :page-sizes="[10, 20, 50]"
        @current-change="load"
        @size-change="query.page = 1; load()"
      />
    </div>

    <el-dialog v-model="detailDialog.visible" title="对话详情" width="640px">
      <template v-if="detailDialog.row">
        <p class="meta-line">
          用户：{{ detailDialog.row.username }} ｜ 模型：{{ detailDialog.row.model }} ｜
          Tokens：{{ detailDialog.row.tokens }} ｜ IP：{{ detailDialog.row.ip }} ｜
          {{ fmtTime(detailDialog.row.created_at) }}
        </p>
        <div class="qa-block q"><b>提问</b><pre>{{ detailDialog.row.prompt }}</pre></div>
        <div class="qa-block a"><b>回答</b><pre>{{ detailDialog.row.answer }}</pre></div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.mono {
  font-family: Consolas, monospace;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.meta-line {
  font-size: 12.5px;
  color: var(--el-text-color-secondary);
  margin: 0 0 12px;
}

.qa-block {
  margin-bottom: 12px;
}

.qa-block b {
  font-size: 13px;
  color: var(--el-text-color-primary);
}

.qa-block pre {
  margin: 6px 0 0;
  padding: 10px 12px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  background: var(--el-bg-color);
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
  max-height: 280px;
  overflow-y: auto;
  font-family: inherit;
}

.qa-block.a pre {
  background: rgba(30, 64, 175, 0.08);
}
</style>
