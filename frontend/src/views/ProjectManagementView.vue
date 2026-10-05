<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { createProject, deleteProject, getProjects, updateProject } from '../api/projects'
import type { Project } from '../api/projects'
import { createBatch, deleteBatch, getProjectBatches, updateBatch } from '../api/batches'
import type { ExperimentBatch } from '../api/batches'
import { getApiErrorMessage } from '../api/errors'
import { formatDateTime } from '../utils/datetime'

const router = useRouter()

const projects = ref<Project[]>([])
const batches = ref<ExperimentBatch[]>([])
const selectedProject = ref<Project | null>(null)
const projectsLoading = ref(false)
const batchesLoading = ref(false)
const projectsError = ref('')
const batchesError = ref('')
const submitting = ref(false)
const deleting = ref(false)
const busy = computed(() => submitting.value || deleting.value)
let batchRequest = 0

const dialogVisible = ref(false)
const dialogKind = ref<'project' | 'batch'>('project')
const editingId = ref<number | null>(null)
const batchProjectId = ref<number | null>(null)
const formRef = ref<FormInstance>()
const form = reactive({ name: '', description: '' })
const entityLabel = computed(() => dialogKind.value === 'project' ? '项目' : '批次')
const dialogTitle = computed(() => `${editingId.value === null ? '新建' : '编辑'}${entityLabel.value}`)
const rules: FormRules<typeof form> = {
  name: [{ required: true, trigger: 'blur', validator: (_rule, value: unknown, callback) => {
    callback(typeof value === 'string' && value.trim() ? undefined : new Error('名称不能为空'))
  } }],
}

function clearSelection(): void {
  selectedProject.value = null
  batches.value = []
  batchesError.value = ''
  batchesLoading.value = false
  batchRequest += 1
}

async function loadProjects(): Promise<void> {
  if (projectsLoading.value) return
  projectsLoading.value = true
  projectsError.value = ''
  try {
    projects.value = await getProjects()
    if (selectedProject.value) {
      const current = projects.value.find(project => project.id === selectedProject.value?.id)
      if (current) selectedProject.value = current
      else clearSelection()
    }
  } catch (error: unknown) {
    projectsError.value = getApiErrorMessage(error, '项目列表加载失败，请稍后重试。')
    ElMessage.error(projectsError.value)
  } finally {
    projectsLoading.value = false
  }
}

async function loadBatches(): Promise<void> {
  const projectId = selectedProject.value?.id
  if (projectId === undefined) return
  const request = ++batchRequest
  batchesLoading.value = true
  batchesError.value = ''
  try {
    const response = await getProjectBatches(projectId)
    if (request === batchRequest && selectedProject.value?.id === projectId) batches.value = response
  } catch (error: unknown) {
    if (request === batchRequest && selectedProject.value?.id === projectId) {
      batchesError.value = getApiErrorMessage(error, '批次列表加载失败，请稍后重试。')
      ElMessage.error(batchesError.value)
    }
  } finally {
    if (request === batchRequest) batchesLoading.value = false
  }
}

function selectProject(project: Project): void {
  selectedProject.value = project
  batches.value = []
  void loadBatches()
}

async function openDialog(kind: 'project' | 'batch', entity?: Project | ExperimentBatch): Promise<void> {
  if (busy.value || (kind === 'batch' && !selectedProject.value)) return
  dialogKind.value = kind
  editingId.value = entity?.id ?? null
  batchProjectId.value = kind === 'batch' ? selectedProject.value!.id : null
  form.name = entity?.name ?? ''
  form.description = entity?.description ?? ''
  dialogVisible.value = true
  await nextTick()
  formRef.value?.clearValidate()
}

async function submitForm(): Promise<void> {
  if (busy.value || !formRef.value) return
  submitting.value = true
  try {
    if (!await formRef.value.validate().catch(() => false)) return
    const payload = { name: form.name.trim(), description: form.description === '' ? null : form.description }
    if (dialogKind.value === 'project') {
      const saved = editingId.value === null
        ? await createProject(payload) : await updateProject(editingId.value, payload)
      if (selectedProject.value?.id === saved.id) selectedProject.value = saved
      dialogVisible.value = false
      ElMessage.success('项目已保存')
      await loadProjects()
    } else {
      const projectId = batchProjectId.value
      if (projectId === null) return
      if (editingId.value === null) await createBatch(projectId, payload)
      else await updateBatch(editingId.value, payload)
      dialogVisible.value = false
      ElMessage.success('批次已保存')
      if (selectedProject.value?.id === projectId) await loadBatches()
    }
  } catch (error: unknown) {
    ElMessage.error(getApiErrorMessage(error))
  } finally {
    submitting.value = false
  }
}

async function removeEntity(kind: 'project' | 'batch', entity: Project | ExperimentBatch): Promise<void> {
  if (busy.value) return
  deleting.value = true
  const label = kind === 'project' ? '项目' : '批次'
  try {
    await ElMessageBox.confirm(`确定删除${label}“${entity.name}”吗？`, '删除确认', {
      confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning', distinguishCancelAndClose: true,
    })
    if (kind === 'project') {
      await deleteProject(entity.id)
      if (selectedProject.value?.id === entity.id) clearSelection()
      ElMessage.success('项目已删除')
      await loadProjects()
    } else {
      await deleteBatch(entity.id)
      ElMessage.success('批次已删除')
      await loadBatches()
    }
  } catch (error: unknown) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(getApiErrorMessage(error))
  } finally {
    deleting.value = false
  }
}

onMounted(loadProjects)
</script>

<template>
  <section class="page-heading">
    <h1>项目管理</h1>
    <p>管理实验项目，选择项目后查看和维护所属实验批次。</p>
  </section>

  <el-card shadow="never" class="management-card">
    <template #header>
      <div class="card-header">
        <h2>实验项目</h2>
        <div class="card-actions">
          <el-button :loading="projectsLoading" :disabled="busy" @click="loadProjects">刷新项目</el-button>
          <el-button type="primary" :disabled="busy || projectsLoading" @click="openDialog('project')">新建项目</el-button>
        </div>
      </div>
    </template>
    <el-alert v-if="projectsError" :title="projectsError" type="error" :closable="false" show-icon />
    <el-empty v-else-if="!projectsLoading && projects.length === 0" description="暂无实验项目">
      <el-button type="primary" :disabled="busy" @click="openDialog('project')">新建项目</el-button>
    </el-empty>
    <el-table v-else v-loading="projectsLoading" :data="projects" row-key="id" aria-label="实验项目列表">
      <el-table-column prop="name" label="名称" min-width="170" show-overflow-tooltip />
      <el-table-column label="描述" min-width="190" show-overflow-tooltip>
        <template #default="{ row }">{{ row.description || '-' }}</template>
      </el-table-column>
      <el-table-column label="创建时间" width="180">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="230">
        <template #default="{ row }">
          <el-button link type="primary" :disabled="busy || projectsLoading" @click="selectProject(row)">查看批次</el-button>
          <el-button link type="primary" :disabled="busy || projectsLoading" @click="openDialog('project', row)">编辑</el-button>
          <el-button link type="danger" :disabled="busy || projectsLoading" @click="removeEntity('project', row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-card shadow="never" class="management-card">
    <template #header>
      <div class="card-header">
        <h2>{{ selectedProject ? `${selectedProject.name} / 实验批次` : '实验批次' }}</h2>
        <div class="card-actions">
          <el-button :loading="batchesLoading" :disabled="!selectedProject || busy" @click="loadBatches">刷新批次</el-button>
          <el-button type="primary" :disabled="!selectedProject || busy || batchesLoading" @click="openDialog('batch')">新建批次</el-button>
        </div>
      </div>
    </template>
    <el-empty v-if="!selectedProject" description="请选择一个实验项目查看批次" />
    <template v-else>
      <p class="current-project">当前项目：{{ selectedProject.name }}</p>
      <el-alert v-if="batchesError" :title="batchesError" type="error" :closable="false" show-icon />
      <el-empty v-else-if="!batchesLoading && batches.length === 0" description="当前项目暂无实验批次" />
      <el-table v-else v-loading="batchesLoading" :data="batches" row-key="id" aria-label="实验批次列表">
        <el-table-column prop="name" label="名称" min-width="170" show-overflow-tooltip />
        <el-table-column label="描述" min-width="190" show-overflow-tooltip>
          <template #default="{ row }">{{ row.description || '-' }}</template>
        </el-table-column>
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="230">
          <template #default="{ row }">
            <el-button link type="primary" :disabled="busy || batchesLoading"
                       @click="router.push({ path: '/experiments', query: { projectId: row.project_id, batchId: row.id } })">管理实验</el-button>
            <el-button link type="primary" :disabled="busy || batchesLoading" @click="openDialog('batch', row)">编辑</el-button>
            <el-button link type="danger" :disabled="busy || batchesLoading" @click="removeEntity('batch', row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </template>
  </el-card>

  <el-dialog v-model="dialogVisible" :title="dialogTitle" width="min(520px, 92vw)"
             :close-on-click-modal="!submitting" :close-on-press-escape="!submitting" :show-close="!submitting">
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top" :disabled="submitting" @submit.prevent="submitForm">
      <el-form-item :label="`${entityLabel}名称`" prop="name">
        <el-input v-model="form.name" :aria-label="`${entityLabel}名称`" />
      </el-form-item>
      <el-form-item :label="`${entityLabel}说明`" prop="description">
        <el-input v-model="form.description" type="textarea" :rows="3" :aria-label="`${entityLabel}说明`" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button :disabled="submitting" @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" :disabled="submitting" @click="submitForm">保存</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.page-heading { margin-bottom: 28px; }
h1 { margin: 0 0 12px; font-size: 28px; }
.page-heading p, .current-project { color: #6b7280; line-height: 1.7; }
.management-card { margin-bottom: 24px; }
.card-header { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 16px; }
h2 { margin: 0; font-size: 18px; overflow-wrap: anywhere; }
.card-actions { display: flex; flex-wrap: wrap; gap: 8px; }
.card-actions .el-button { margin-left: 0; }
.current-project { margin-top: 0; overflow-wrap: anywhere; }
</style>
