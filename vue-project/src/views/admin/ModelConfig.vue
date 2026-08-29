<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import http from '@/api'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const loading = ref(false)
const saving = ref(false)
const form = reactive({ base_url: '', api_key: '', protocol: 'openai', model: '' })
const info = reactive({ updated_by: '', updated_at: '' })

async function load() {
  loading.value = true
  try {
    const data = await http.get('/api/model-config')
    form.base_url = data.base_url
    form.api_key = data.api_key // 后端已打码；原样提交会视为保留
    form.protocol = data.protocol
    form.model = data.model
    info.updated_by = data.updated_by
    info.updated_at = data.updated_at
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!form.base_url.startsWith('http://') && !form.base_url.startsWith('https://')) {
    ElMessage.warning('接口地址必须以 http:// 或 https:// 开头')
    return
  }
  if (!form.model.trim()) {
    ElMessage.warning('请填写模型名称')
    return
  }
  saving.value = true
  try {
    // 打码值（****开头）表示未修改密钥 → 提交空字符串让后端保留原密钥
    const apiKey = form.api_key && !form.api_key.startsWith('****') ? form.api_key : ''
    await http.put('/api/model-config', {
      base_url: form.base_url.trim(),
      api_key: apiKey,
      protocol: form.protocol,
      model: form.model.trim(),
    })
    ElMessage.success('配置已保存并即时生效')
    load()
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="admin-page">
    <h2 class="page-title">模型接入</h2>

    <div class="panel" v-loading="loading">
      <div class="panel-head">
        <b>本地 / 自建大模型 API 配置</b>
        <span class="panel-hint">保存后即时生效：BFF 每次对话实时读取，无需重启服务</span>
      </div>
      <div class="panel-body form-body">
        <el-form label-width="110px" style="max-width: 620px">
          <el-form-item label="接口地址">
            <el-input v-model="form.base_url" placeholder="如 https://api.deepseek.com 或 http://127.0.0.1:9190/v1" />
            <div class="field-hint">OpenAI 兼容服务填根地址或 /v1；llama.cpp 原生协议填服务根地址</div>
          </el-form-item>
          <el-form-item label="API Key">
            <el-input v-model="form.api_key" type="password" show-password placeholder="密钥仅保存在服务端；已保存的密钥显示为 ****（不改则保留原值）" />
          </el-form-item>
          <el-form-item label="协议">
            <el-select v-model="form.protocol" style="width: 220px">
              <el-option label="OpenAI 兼容（vLLM / Ollama / DeepSeek…）" value="openai" />
              <el-option label="llama.cpp 原生 /completion" value="llamacpp" />
            </el-select>
          </el-form-item>
          <el-form-item label="模型名称">
            <el-input v-model="form.model" placeholder="如 deepseek-chat / qwen2.5-7b-instruct" />
          </el-form-item>
          <el-form-item>
            <el-button v-if="auth.hasPerm('model:edit')" type="primary" :loading="saving" @click="save">
              保存并生效
            </el-button>
            <span v-if="info.updated_at" class="update-info">
              上次修改：{{ info.updated_by }} · {{ info.updated_at.replace('T', ' ').slice(0, 19) }}
            </span>
          </el-form-item>
        </el-form>
      </div>
    </div>

    <div class="panel">
      <div class="panel-head"><b>说明</b></div>
      <div class="panel-body">
        <ul class="tips">
          <li>配置链路：管理平台 → MySQL（持久）+ Redis（运行时）→ 对话 BFF 每次请求实时读取</li>
          <li>接口地址、协议、模型名修改后，下一次对话即按新配置调用；密钥仅存服务端，前端不回显明文</li>
          <li>修改操作会写入审计日志（model_config.update），可溯源</li>
          <li>切换协议需确保目标服务支持对应协议：openai = OpenAI 兼容；llamacpp = llama.cpp 原生 /completion</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<style scoped>
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
  padding: 18px 20px;
}

.field-hint {
  font-size: 11.5px;
  color: var(--el-text-color-placeholder);
  line-height: 1.5;
  margin-top: 4px;
}

.update-info {
  margin-left: 14px;
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}

.tips {
  margin: 0;
  padding-left: 18px;
  font-size: 13px;
  color: var(--el-text-color-regular);
  line-height: 2;
}
</style>
