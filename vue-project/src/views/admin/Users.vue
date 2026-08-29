<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Search } from '@element-plus/icons-vue'

import http from '@/api'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const loading = ref(false)
const list = ref([])
const total = ref(0)
const roles = ref([])
const query = reactive({ page: 1, size: 10, keyword: '', status: null, role_id: null })

const dialog = reactive({ visible: false, mode: 'create' }) // create | edit
const form = reactive({ id: null, username: '', password: '', phone: '', email: '', role_id: null })
const roleDialog = reactive({ visible: false, userId: null, username: '', roleId: null })

// ---- 新建分组（建组+勾选用户一步完成）----
const grouping = ref(false)
const groupName = ref('')
const selectedUsers = ref([])
const creatingGroup = ref(false)

function startGrouping() {
  grouping.value = true
  groupName.value = ''
  selectedUsers.value = []
}

function onSelectionChange(rows) {
  selectedUsers.value = rows
}

async function confirmGroup() {
  const name = groupName.value.trim()
  if (!name) {
    ElMessage.warning('请输入分组名称')
    return
  }
  creatingGroup.value = true
  try {
    const data = await http.post('/api/groups', {
      name,
      description: '',
      user_ids: selectedUsers.value.map((u) => u.id),
    })
    ElMessage.success(`分组「${data.name}」创建成功，已加入 ${data.member_count} 名用户`)
    grouping.value = false
    groupName.value = ''
    load()
  } finally {
    creatingGroup.value = false
  }
}

async function load() {
  loading.value = true
  try {
    const data = await http.get('/api/users', {
      params: {
        page: query.page,
        size: query.size,
        keyword: query.keyword || undefined,
        status: query.status ?? undefined,
        role_id: query.role_id ?? undefined,
      },
    })
    list.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function loadRoles() {
  if (!auth.hasPerm('role:list')) return
  roles.value = await http.get('/api/roles')
}

function openCreate() {
  dialog.mode = 'create'
  Object.assign(form, { id: null, username: '', password: '', phone: '', email: '', role_id: null })
  dialog.visible = true
}

function openEdit(row) {
  dialog.mode = 'edit'
  Object.assign(form, {
    id: row.id,
    username: row.username,
    password: '',
    phone: row.phone,
    email: row.email,
    role_id: row.role_id,
  })
  dialog.visible = true
}

async function submit() {
  if (!form.username || (dialog.mode === 'create' && !form.password)) {
    ElMessage.warning('请填写完整信息（新建用户需设置密码）')
    return
  }
  if (dialog.mode === 'create') {
    await http.post('/api/users', {
      username: form.username,
      password: form.password,
      phone: form.phone,
      email: form.email,
      role_id: form.role_id,
    })
    ElMessage.success('创建成功')
  } else {
    await http.put(`/api/users/${form.id}`, { phone: form.phone, email: form.email })
    ElMessage.success('已保存')
  }
  dialog.visible = false
  load()
}

async function toggleStatus(row) {
  const next = row.status === 1 ? 0 : 1
  const tip = next === 0 ? '禁用后该用户将立即无法登录和调用 AI，确定？' : '确定启用该用户？'
  try {
    await ElMessageBox.confirm(tip, '提示', { type: 'warning' })
  } catch {
    return
  }
  await http.post(`/api/users/${row.id}/status`, { status: next })
  ElMessage.success(next === 0 ? '已禁用' : '已启用')
  load()
}

async function onResetPassword(row) {
  try {
    const { value } = await ElMessageBox.prompt(
      `为「${row.username}」设置新密码（至少 8 位）`,
      '重置密码',
      { inputType: 'password', inputPattern: /^.{8,}$/, inputErrorMessage: '至少 8 位' },
    )
    await http.post(`/api/users/${row.id}/reset-password`, { new_password: value })
    ElMessage.success('密码已重置')
  } catch {
    /* 取消 */
  }
}

function openAssignRole(row) {
  Object.assign(roleDialog, { visible: true, userId: row.id, username: row.username, roleId: row.role_id })
}

async function submitAssignRole() {
  await http.put(`/api/users/${roleDialog.userId}/role`, { role_id: roleDialog.roleId })
  ElMessage.success('角色已更新')
  roleDialog.visible = false
  load()
}

async function onDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除用户「${row.username}」？`, '警告', { type: 'error' })
  } catch {
    return
  }
  await http.delete(`/api/users/${row.id}`)
  ElMessage.success('已删除')
  load()
}

function fmtTime(v) {
  return v ? String(v).replace('T', ' ').slice(0, 19) : '—'
}

onMounted(() => {
  load()
  loadRoles()
})
</script>

<template>
  <div class="admin-page">
    <h2 class="page-title">用户管理</h2>

    <!-- 分组模式工具条：命名 + 勾选 + 确认分组 -->
    <div v-if="grouping" class="toolbar grouping-bar">
      <span class="grouping-label">分组名称</span>
      <el-input
        v-model="groupName"
        placeholder="自定义命名，如：客服一组"
        maxlength="64"
        style="width: 220px"
        @keyup.enter="confirmGroup"
      />
      <el-tag size="small" effect="plain">已勾选 {{ selectedUsers.length }} 人</el-tag>
      <el-button type="primary" :loading="creatingGroup" @click="confirmGroup">确认分组</el-button>
      <el-button @click="grouping = false">取消</el-button>
    </div>

    <!-- 常规工具条 -->
    <div v-else class="toolbar">
      <el-input
        v-model="query.keyword"
        placeholder="搜索用户名 / 手机 / 邮箱"
        style="width: 240px"
        clearable
        :prefix-icon="Search"
        @keyup.enter="query.page = 1; load()"
        @clear="query.page = 1; load()"
      />
      <el-select v-model="query.status" placeholder="状态" clearable style="width: 110px" @change="query.page = 1; load()">
        <el-option label="启用" :value="1" />
        <el-option label="禁用" :value="0" />
      </el-select>
      <el-select v-model="query.role_id" placeholder="角色" clearable style="width: 140px" @change="query.page = 1; load()">
        <el-option v-for="r in roles" :key="r.id" :label="r.name" :value="r.id" />
      </el-select>
      <el-button :icon="Search" @click="query.page = 1; load()">查询</el-button>
      <el-button :icon="Refresh" @click="load">刷新</el-button>
      <span class="spacer"></span>
      <el-button v-if="auth.hasPerm('group:create')" :icon="Plus" @click="startGrouping">新建分组</el-button>
      <el-button v-if="auth.hasPerm('user:create')" type="primary" :icon="Plus" @click="openCreate">
        新增用户
      </el-button>
    </div>

    <el-table
      v-loading="loading"
      :data="list"
      border
      stripe
      row-key="id"
      style="width: 100%"
      @selection-change="onSelectionChange"
    >
      <!-- 分组模式下出现勾选框 -->
      <el-table-column v-if="grouping" type="selection" width="42" />
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="username" label="用户名" min-width="120" />
      <el-table-column prop="phone" label="手机号" width="130">
        <template #default="{ row }">{{ row.phone || '—' }}</template>
      </el-table-column>
      <el-table-column prop="email" label="邮箱" min-width="160">
        <template #default="{ row }">{{ row.email || '—' }}</template>
      </el-table-column>
      <el-table-column label="角色" width="110">
        <template #default="{ row }">
          <el-tag size="small" effect="plain">{{ row.role_name }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="所属分组" min-width="130">
        <template #default="{ row }">
          <template v-if="row.groups && row.groups.length">
            <el-tag v-for="g in row.groups" :key="g" size="small" type="info" effect="plain" class="group-tag">
              {{ g }}
            </el-tag>
          </template>
          <span v-else class="no-group">—</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-switch
            :model-value="row.status === 1"
            :disabled="!auth.hasPerm('user:status')"
            @change="toggleStatus(row)"
          />
        </template>
      </el-table-column>
      <el-table-column label="最后登录" width="165">
        <template #default="{ row }">{{ fmtTime(row.last_login_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="300" fixed="right">
        <template #default="{ row }">
          <el-button v-if="auth.hasPerm('user:edit')" link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button v-if="auth.hasPerm('user:assign_role')" link type="primary" @click="openAssignRole(row)">
            分配角色
          </el-button>
          <el-button v-if="auth.hasPerm('user:reset_password')" link type="warning" @click="onResetPassword(row)">
            重置密码
          </el-button>
          <el-button v-if="auth.hasPerm('user:delete')" link type="danger" @click="onDelete(row)">删除</el-button>
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

    <!-- 新增/编辑 -->
    <el-dialog v-model="dialog.visible" :title="dialog.mode === 'create' ? '新增用户' : '编辑用户'" width="440px">
      <el-form label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="form.username" :disabled="dialog.mode === 'edit'" placeholder="字母/数字/下划线" />
        </el-form-item>
        <el-form-item v-if="dialog.mode === 'create'" label="初始密码">
          <el-input v-model="form.password" type="password" show-password placeholder="至少 8 位" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="form.phone" placeholder="选填" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" placeholder="选填" />
        </el-form-item>
        <el-form-item v-if="dialog.mode === 'create'" label="角色">
          <el-select v-model="form.role_id" placeholder="选择角色" style="width: 100%">
            <el-option v-for="r in roles" :key="r.id" :label="r.name" :value="r.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 分配角色 -->
    <el-dialog v-model="roleDialog.visible" :title="`分配角色 · ${roleDialog.username}`" width="380px">
      <el-select v-model="roleDialog.roleId" style="width: 100%" placeholder="选择角色">
        <el-option v-for="r in roles" :key="r.id" :label="r.name" :value="r.id" />
      </el-select>
      <template #footer>
        <el-button @click="roleDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitAssignRole">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.group-tag {
  margin-right: 4px;
}

.no-group {
  color: var(--el-text-color-placeholder);
}

.grouping-bar {
  padding: 10px 14px;
  border: 1px solid rgba(30, 64, 175, 0.4);
  border-radius: 8px;
  background: rgba(30, 64, 175, 0.08);
}

.grouping-label {
  font-size: 13px;
  color: var(--el-text-color-regular);
}
</style>
