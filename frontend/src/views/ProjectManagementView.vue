<script setup lang="ts">
import { nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { createProject, deleteProject, getProjects, updateProject } from '../api/projects'
import type { Project } from '../api/projects'
import { getApiErrorMessage } from '../api/errors'
import { formatDateTime } from '../utils/datetime'

const router = useRouter()
const route = useRoute()
const continueAction = ref<'new-experiment' | 'manage-batches' | ''>('')
const projects = ref<Project[]>([])
const loading = ref(false)
const busy = ref(false)
const error = ref('')
const dialog = ref(false)
const editing = ref<number | null>(null)
const formRef = ref<FormInstance>()
const form = reactive({ name: '', description: '' })
const rules: FormRules = { name: [{ required: true, whitespace: true, message: '项目名称不能为空', trigger: 'blur' }] }
async function load(): Promise<void> {
  if (loading.value) return
  loading.value = true; error.value = ''
  try { projects.value = await getProjects() }
  catch (exception) { error.value = getApiErrorMessage(exception, '项目加载失败，请重试。') }
  finally { loading.value = false }
}
async function open(project?: Project): Promise<void> {
  continueAction.value = ''
  editing.value = project?.id ?? null
  form.name = project?.name ?? ''; form.description = project?.description ?? ''
  dialog.value = true
  await nextTick(); formRef.value?.clearValidate()
}
async function save(): Promise<void> {
  if (busy.value || !await formRef.value?.validate().catch(() => false)) return
  busy.value = true
  try {
    const payload = { name: form.name.trim(), description: form.description || null }
    const saved = editing.value === null ? await createProject(payload) : await updateProject(editing.value, payload)
    const nextAction = continueAction.value
    continueAction.value = ''
    dialog.value = false; ElMessage.success('项目已保存'); await load()
    if (nextAction) await router.push({ path: '/experiments', query: { projectId: saved.id, action: nextAction } })
  } catch (exception) { ElMessage.error(getApiErrorMessage(exception)) }
  finally { busy.value = false }
}
async function remove(project: Project): Promise<void> {
  if (busy.value) return
  busy.value = true
  try {
    await ElMessageBox.confirm(`确定删除项目“${project.name}”吗？包含批次的项目不能删除。`, '删除确认', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' })
    await deleteProject(project.id); ElMessage.success('项目已删除'); await load()
  } catch (exception) { if (exception !== 'cancel' && exception !== 'close') ElMessage.error(getApiErrorMessage(exception)) }
  finally { busy.value = false }
}
onMounted(load)
watch(() => route.query.action, async action => {
  if (action !== 'create') return
  const nextAction = route.query.next
  const query = { ...route.query }; delete query.action; delete query.next
  await router.replace({ path: route.path, query })
  await open()
  continueAction.value = nextAction === 'new-experiment' || nextAction === 'manage-batches' ? nextAction : ''
}, { immediate: true })
</script>

<template>
  <section class="page-heading"><h1>项目管理</h1></section>
  <el-card shadow="never" class="management-card">
    <template #header><div class="card-header"><h2>实验项目</h2><div class="card-actions">
      <el-button :loading="loading" :disabled="busy" @click="load">刷新项目</el-button>
      <el-button type="primary" :disabled="busy || loading" @click="open()">新建项目</el-button>
    </div></div></template>
    <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
    <el-empty v-else-if="!loading && !projects.length" description="暂无实验项目"><el-button type="primary" @click="open()">新建项目</el-button></el-empty>
    <el-table v-else :data="projects" v-loading="loading" row-key="id" aria-label="实验项目列表">
      <el-table-column prop="name" label="名称" min-width="220" show-overflow-tooltip />
      <el-table-column prop="description" label="描述" min-width="220" show-overflow-tooltip />
      <el-table-column label="创建时间" width="180"><template #default="{ row }">{{ formatDateTime(row.created_at) }}</template></el-table-column>
      <el-table-column label="操作" width="230"><template #default="{ row }">
        <el-button link type="primary" :disabled="busy" @click="router.push({ path: '/experiments', query: { projectId: row.id } })">进入项目</el-button>
        <el-button link type="primary" :disabled="busy" @click="open(row)">编辑</el-button>
        <el-button link type="danger" :disabled="busy" @click="remove(row)">删除</el-button>
      </template></el-table-column>
    </el-table>
  </el-card>
  <el-dialog v-model="dialog" :title="editing === null ? '新建项目' : '编辑项目'" width="min(520px, 92vw)" :close-on-click-modal="!busy" :close-on-press-escape="!busy" :show-close="!busy" @closed="continueAction = ''">
    <p v-if="continueAction" class="hint">保存项目后，将继续{{ continueAction === 'new-experiment' ? '建立批次并新建实验' : '建立实验批次' }}。</p>
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top" :disabled="busy" @submit.prevent="save">
      <el-form-item label="项目名称" prop="name"><el-input v-model="form.name" aria-label="项目名称" /></el-form-item>
      <el-form-item label="项目说明"><el-input v-model="form.description" type="textarea" :rows="3" aria-label="项目说明" /></el-form-item>
    </el-form>
    <template #footer><el-button :disabled="busy" @click="dialog = false">取消</el-button><el-button type="primary" :loading="busy" @click="save">保存项目</el-button></template>
  </el-dialog>
</template>
