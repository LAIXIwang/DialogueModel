<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

import http from '@/api'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const list = ref([])
const permissions = ref([])
const loading = ref(false)

const dialog = reactive({ visible: false, mode: 'create', id: null, code: '', name: '', description: '' })
const permDialog = reactive({ visible: false, roleId: null, roleName: '', checked: [] })
const saving = ref(false)

// 权限按模块分组
const permGroups = computed(() => {
  const groups = {}
  for (const p of permissions.value) {
    ;(groups[p.module] ||= []).push(p)
  }
  return Object.entries(groups)
})

async function load() {
  loading.value = true
  try {
    list.value = await http.get('/api/roles')
  } finally {
    loading.value = false
  }
}

async function loadPermissions() {
  permissions.value = await http.get('/api/permissions')
}

function openCreate() {
  Object.assign(dialog, { visible: true, mode: 'create', id: null, code: '', name: '', description: '' })
}

function openEdit(row) {
  Object.assign(dialog, {
    visible: true,
    mode: 'edit',
    id: row.id,
    code: row.code,
    name: row.name,
    description: row.description,
  })
}

async function submit() {
  if (dialog.mode === 'create') {
    await http.post('/api/roles', { code: dialog.code, name: dialog.name, description: dialog.description })
    ElMessage.success('创建成功')
  } else {
    await http.put(`/api/roles/${dialog.id}`, { name: dialog.name, description: dialog.description })
    ElMessage.success('已保存')
  }
  dialog.visible = false
  load()
}

async function onDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除角色「${row.name}」？`, '警告', { type: 'error' })
  } catch {
    return
  }
  await http.delete(`/api/roles/${row.id}`)
  ElMessage.success('已删除')
  load()
}

async function openAssignPerm(row) {
  const ids = await http.get(`/api/roles/${row.id}/permissions`)
  Object.assign(permDialog, { visible: true, roleId: row.id, roleName: row.name, checked: [...ids] })
}

async function submitPerm() {
  saving.value = true
  try {
    await http.put(`/api/roles/${permDialog.roleId}/permissions`, { permission_ids: permDialog.checked })
    ElMessage.success('权限已更新')
    permDialog.visible = false
    load()
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  load()
  if (auth.hasPerm('permission:list')) loadPermissions()
})
</script>

<template>
  <div class="admin-page">
    <h2 class="page-title">角色权限</h2>

    <div class="toolbar">
      <span class="hint">RBAC 基于角色的权限模型 · 超级管理员默认拥有全部权限</span>
      <span class="spacer"></span>
      <el-button v-if="auth.hasPerm('role:create')" type="primary" :icon="Plus" @click="openCreate">
        新增角色
      </el-button>
    </div>

    <el-table v-loading="loading" :data="list" border stripe style="width: 100%">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="code" label="编码" width="140" />
      <el-table-column prop="name" label="角色名称" width="140" />
      <el-table-column prop="description" label="描述" min-width="180">
        <template #default="{ row }">{{ row.description || '—' }}</template>
      </el-table-column>
      <el-table-column label="用户数" width="90" align="center">
        <template #default="{ row }">{{ row.user_count }}</template>
      </el-table-column>
      <el-table-column label="权限数" width="90" align="center">
        <template #default="{ row }">{{ row.permission_ids.length }}</template>
      </el-table-column>
      <el-table-column label="操作" width="240" fixed="right">
        <template #default="{ row }">
          <el-button v-if="auth.hasPerm('role:edit')" link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button
            v-if="auth.hasPerm('role:assign_permission') && row.code !== 'super_admin'"
            link
            type="primary"
            @click="openAssignPerm(row)"
          >
            分配权限
          </el-button>
          <el-button v-if="auth.hasPerm('role:delete')" link type="danger" @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新增/编辑角色 -->
    <el-dialog v-model="dialog.visible" :title="dialog.mode === 'create' ? '新增角色' : '编辑角色'" width="420px">
      <el-form label-width="80px">
        <el-form-item label="编码">
          <el-input v-model="dialog.code" :disabled="dialog.mode === 'edit'" placeholder="如 ops" />
        </el-form-item>
        <el-form-item label="名称">
          <el-input v-model="dialog.name" placeholder="如 运维" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="dialog.description" type="textarea" :rows="2" placeholder="选填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 分配权限 -->
    <el-dialog v-model="permDialog.visible" :title="`分配权限 · ${permDialog.roleName}`" width="560px">
      <el-checkbox-group v-model="permDialog.checked">
        <div v-for="[module, perms] in permGroups" :key="module" class="perm-group">
          <div class="perm-module">{{ module }}</div>
          <el-checkbox v-for="p in perms" :key="p.id" :value="p.id" class="perm-item">
            {{ p.name }} <span class="perm-code">{{ p.code }}</span>
          </el-checkbox>
        </div>
      </el-checkbox-group>
      <template #footer>
        <el-button @click="permDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitPerm">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.hint {
  font-size: 12.5px;
  color: var(--el-text-color-secondary);
}

.perm-group {
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 1px dashed var(--el-border-color-lighter);
}

.perm-module {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin-bottom: 8px;
}

.perm-item {
  margin-right: 16px;
  margin-bottom: 6px;
}

.perm-code {
  color: var(--el-text-color-placeholder);
  font-size: 11px;
  margin-left: 4px;
}
</style>
