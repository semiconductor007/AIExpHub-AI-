<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { getProjects } from '../api/projects'
import type { Project } from '../api/projects'
import { getApiErrorMessage } from '../api/errors'
const router = useRouter()
const visible = ref(false)
const loading = ref(false)
const error = ref('')
const projects = ref<Project[]>([])
const projectId = ref<number | null>(null)
const action = ref<'new-experiment' | 'manage-batches' | ''>('')
let request = 0
async function load(): Promise<void> {
  const current = ++request
  loading.value = true; error.value = ''
  try {
    const response = await getProjects()
    if (current !== request) return
    projects.value = response
    if (!response.some(item => item.id === projectId.value)) projectId.value = response.length === 1 ? response[0]!.id : null
  } catch (exception) { if (current === request) error.value = getApiErrorMessage(exception, '项目加载失败，请重试。') }
  finally { if (current === request) loading.value = false }
}
function open(intent: typeof action.value = ''): void {
  action.value = intent; projectId.value = null; projects.value = []; visible.value = true; void load()
}
function continueToProject(): void {
  if (projectId.value === null || loading.value || error.value) return
  visible.value = false
  void router.push({ path: '/experiments', query: { projectId: projectId.value, ...(action.value ? { action: action.value } : {}) } })
}
function createFirstProject(): void {
  visible.value = false
  void router.push({ path: '/projects', query: { action: 'create', ...(action.value ? { next: action.value } : {}) } })
}
defineExpose({ open })
</script>
<template>
  <el-dialog v-model="visible" :title="action === 'new-experiment' ? '新建实验 · 选择项目' : action === 'manage-batches' ? '建立批次 · 选择项目' : '进入项目工作区'" width="min(500px, 92vw)">
    <p class="picker-hint">{{ action === 'new-experiment' ? '先选择研究主题，再填写所属批次、模型和参数。' : '选择要操作的实验项目。' }}</p>
    <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
    <div v-loading="loading" class="picker-body">
      <el-empty v-if="!loading && !error && !projects.length" description="还没有实验项目，从创建项目开始。"><el-button type="primary" @click="createFirstProject">创建项目并继续</el-button></el-empty>
      <el-select v-else v-model="projectId" aria-label="选择目标项目" placeholder="请选择实验项目" :disabled="loading || !!error" style="width: 100%"><el-option v-for="project in projects" :key="project.id" :label="project.name" :value="project.id" /></el-select>
    </div>
    <template #footer><el-button @click="visible = false">取消</el-button><el-button v-if="error" :loading="loading" @click="load">重新加载项目</el-button><el-button v-else-if="projects.length" type="primary" :disabled="loading || projectId === null" @click="continueToProject">{{ action === 'new-experiment' ? '继续新建实验' : '进入工作区' }}</el-button></template>
  </el-dialog>
</template>
<style scoped>
.picker-hint { margin: 0 0 20px; color: #64748b; line-height: 1.7; }.picker-body { min-height: 60px; padding-top: 8px; }
</style>
