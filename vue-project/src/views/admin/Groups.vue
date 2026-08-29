<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

import http from '@/api'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const list = ref([])
const permissions = ref([])
const allUsers = ref([])
const loading = ref(false)
const saving = ref(false)

const dialog = reactive({ visible: false, mode: 'create', id: null, name: '', description: '' })
const memberDialog = reactive({ visible: false, groupId: null, groupName: '', selected: [] })
const permDialog = reactive({ visible: false, groupId: null, groupName: '', checked: [] })

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
    list.value = await http.get('/api/groups')
  } finally {
    loading.value = false
  }
}

async function loadExtras() {
  if (auth.hasPerm('permission:list')) permissions.value = await http.get('/api/permissions')
  if (auth.hasPerm('user:list')) await loadAllUsers()
}

// 分页拉取全部用户（接口单页上限 100）
async function loadAllUsers() {
  const all = []
  let page = 1
  const size = 100
  while (page <= 10) {
    const data = await http.get('/api/users', { params: { page, size } })
    all.push(...data.items)
    if (all.length >= data.total || data.items.length < size) break
    page++
  }
  allUsers.value = all
}

function openCreate() {
  Object.assign(dialog, { visible: true, mode: 'create', id: null, name: '', description: '' })
}

function openEdit(row) {
  Object.assign(dialog, {
    visible: true,
    mode: 'edit',
    id: row.id,
    name: row.name,
    description: row.description,
  })
}

async function submit() {
  if (!dialog.name.trim()) {
    ElMessage.warning('请输入分组名称')
    return
  }
  if (dialog.mode === 'create') {
    await http.post('/api/groups', { name: dialog.name.trim(), description: dialog.description })
    ElMessage.success('分组创建成功')
  } else {
    await http.put(`/api/groups/${dialog.id}`, { name: dialog.name.trim(), description: dialog.description })
    ElMessage.success('已保存')
  }
  dialog.visible = false
  load()
}

async function onDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除分组「${row.name}」？组内 ${row.member_count} 名成员与权限关系将一并解除。`,
      '警告',
      { type: 'error' },
    )
  } catch {
    return
  }
  await http.delete(`/api/groups/${row.id}`)
  ElMessage.success('分组已删除')
  load()
}

async function openMembers(row) {
  const members = await http.get(`/api/groups/${row.id}/members`)
  Object.assign(memberDialog, {
    visible: true,
    groupId: row.id,
    groupName: row.name,
    selected: members.map((m) => m.id),
  })
}

async function submitMembers() {
  saving.value = true
  try {
    const data = await http.put(`/api/groups/${memberDialog.groupId}/members`, {
      user_ids: memberDialog.selected,
    })
    ElMessage.success(`已统一分配 ${data.member_count} 名用户`)
    memberDialog.visible = false
    load()
  } finally {
    saving.value = false
  }
}

async function openPerms(row) {
  const ids = await http.get(`/api/groups/${row.id}/permissions`)
  Object.assign(permDialog, {
    visible: true,
    groupId: row.id,
    groupName: row.name,
    checked: [...ids],
  })
}

async function submitPerms() {
  saving.value = true
  try {
    await http.put(`/api/groups/${permDialog.groupId}/permissions`, {
      permission_ids: permDialog.checked,
    })
    ElMessage.success('分组权限已统一更新')
    permDialog.visible = false
    load()
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  load()
  loadExtras()
})
</script>

<template>
  <div class="admin-page">
    <h2 class="page-title">分组管理</h2>

    <div class="toolbar">
      <span class="hint">自定义命名分组 · 多选用户统一入组 · 分组级权限统一分配（用户权限 = 角色权限 ∪ 分组权限）</span>
      <span class="spacer"></span>
      <el-button v-if="auth.hasPerm('group:create')" type="primary" :icon="Plus" @click="openCreate">
        新建分组
      </el-button>
    </div>

    <el-table v-loading="loading" :data="list" border stripe style="width: 100%">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="name" label="分组名称" min-width="150" />
      <el-table-column prop="description" label="描述" min-width="200">
        <template #default="{ row }">{{ row.description || '—' }}</template>
      </el-table-column>
      <el-table-column label="成员数" width="100" align="center">
        <template #default="{ row }">
          <el-tag size="small" effect="plain">{{ row.member_count }} 人</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="权限数" width="100" align="center">
        <template #default="{ row }">{{ row.permission_ids.length }} 项</template>
      </el-table-column>
      <el-table-column label="操作" width="300" fixed="right">
        <template #default="{ row }">
          <el-button v-if="auth.hasPerm('group:edit')" link type="primary" @click="openEdit(row)">重命名</el-button>
          <el-button v-if="auth.hasPerm('group:assign_member')" link type="primary" @click="openMembers(row)">
            成员
          </el-button>
          <el-button v-if="auth.hasPerm('group:assign_permission')" link type="primary" @click="openPerms(row)">
            权限
          </el-button>
          <el-button v-if="auth.hasPerm('group:delete')" link type="danger" @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新建/重命名 -->
    <el-dialog v-model="dialog.visible" :title="dialog.mode === 'create' ? '新建分组' : '重命名分组'" width="420px">
      <el-form label-width="80px">
        <el-form-item label="分组名称">
          <el-input v-model="dialog.name" placeholder="自定义命名，如：客服一组" maxlength="64" />
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

    <!-- 成员分配（多选） -->
    <el-dialog v-model="memberDialog.visible" :title="`成员分配 · ${memberDialog.groupName}`" width="480px">
      <p class="dialog-hint">勾选多个用户统一加入该分组（保存后整体替换）</p>
      <el-select v-model="memberDialog.selected" multiple filterable placeholder="选择用户（可多选/搜索）" style="width: 100%">
        <el-option v-for="u in allUsers" :key="u.id" :label="`${u.username}（${u.role_name}）`" :value="u.id" />
      </el-select>
      <template #footer>
        <el-button @click="memberDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitMembers">
          保存（{{ memberDialog.selected.length }} 人）
        </el-button>
      </template>
    </el-dialog>

    <!-- 权限分配 -->
    <el-dialog v-model="permDialog.visible" :title="`权限分配 · ${permDialog.groupName}`" width="560px">
      <p class="dialog-hint">所选权限将统一授予组内全部成员</p>
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
        <el-button type="primary" :loading="saving" @click="submitPerms">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.hint {
  font-size: 12.5px;
  color: var(--el-text-color-secondary);
}

.dialog-hint {
  margin: 0 0 10px;
  font-size: 12.5px;
  color: var(--el-text-color-placeholder);
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
