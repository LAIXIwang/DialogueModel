<script setup>
import { onMounted, reactive, ref } from 'vue'
import { Refresh, Search } from '@element-plus/icons-vue'

import http from '@/api'

const loading = ref(false)
const list = ref([])
const total = ref(0)
const actions = ref([])
const query = reactive({ page: 1, size: 10, action: '', username: '', ip: '' })

async function load() {
  loading.value = true
  try {
    const data = await http.get('/api/logs', {
      params: {
        page: query.page,
        size: query.size,
        action: query.action || undefined,
        username: query.username || undefined,
        ip: query.ip || undefined,
      },
    })
    list.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function loadActions() {
  actions.value = await http.get('/api/logs/actions')
}

function fmtTime(v) {
  return v ? String(v).replace('T', ' ').slice(0, 19) : '—'
}

function fmtParams(params) {
  if (!params || params === '{}') return '—'
  return params
}

onMounted(() => {
  load()
  loadActions()
})
</script>

<template>
  <div class="admin-page">
    <h2 class="page-title">审计日志</h2>

    <div class="toolbar">
      <el-select v-model="query.action" placeholder="操作类型" clearable filterable style="width: 180px" @change="query.page = 1; load()">
        <el-option v-for="a in actions" :key="a.value" :label="a.label" :value="a.value" />
      </el-select>
      <el-input
        v-model="query.username"
        placeholder="操作者"
        style="width: 140px"
        clearable
        @keyup.enter="query.page = 1; load()"
        @clear="query.page = 1; load()"
      />
      <el-input
        v-model="query.ip"
        placeholder="IP 溯源"
        style="width: 150px"
        clearable
        @keyup.enter="query.page = 1; load()"
        @clear="query.page = 1; load()"
      />
      <el-button :icon="Search" @click="query.page = 1; load()">查询</el-button>
      <el-button :icon="Refresh" @click="load">刷新</el-button>
      <span class="spacer"></span>
      <span class="hint">登录记录 · 后台操作 · AI 调用 · IP 溯源</span>
    </div>

    <el-table v-loading="loading" :data="list" border stripe style="width: 100%">
      <el-table-column prop="id" label="ID" width="90" />
      <el-table-column prop="username" label="操作者" width="120">
        <template #default="{ row }">{{ row.username || '—' }}</template>
      </el-table-column>
      <el-table-column label="行为" width="150">
        <template #default="{ row }">
          <el-tag size="small" effect="plain">{{ row.action }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="ip" label="IP" width="140" />
      <el-table-column label="参数" min-width="240" show-overflow-tooltip>
        <template #default="{ row }">{{ fmtParams(row.params) }}</template>
      </el-table-column>
      <el-table-column label="说明" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">{{ row.detail || '—' }}</template>
      </el-table-column>
      <el-table-column label="时间" width="165">
        <template #default="{ row }">{{ fmtTime(row.created_at) }}</template>
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
  </div>
</template>

<style scoped>
.hint {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}
</style>
