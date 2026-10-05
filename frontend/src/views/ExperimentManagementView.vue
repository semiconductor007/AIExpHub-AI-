<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { getProjects } from '../api/projects'
import type { Project } from '../api/projects'
import { getProjectBatches } from '../api/batches'
import type { ExperimentBatch } from '../api/batches'
import { createExperiment, deleteExperiment, getBatchExperiments, updateExperiment } from '../api/experiments'
import type { Experiment } from '../api/experiments'
import { createExperimentResult, getExperimentResult, updateExperimentResult } from '../api/results'
import type { ExperimentResult, ResultMetric, ResultPayload } from '../api/results'
import { getApiErrorMessage, isApiErrorDetail } from '../api/errors'
import { formatDateTime } from '../utils/datetime'

const route = useRoute()
const router = useRouter()
const projects = ref<Project[]>([])
const batches = ref<ExperimentBatch[]>([])
const experiments = ref<Experiment[]>([])
const projectId = ref<number | null>(null)
const batchId = ref<number | null>(null)
const selectedExperiment = ref<Experiment | null>(null)
const result = ref<ExperimentResult | null>(null)
const resultMissing = ref(false)
const selectedBatch = computed(() => batches.value.find(batch => batch.id === batchId.value))
const projectsLoading = ref(false)
const batchesLoading = ref(false)
const experimentsLoading = ref(false)
const resultLoading = ref(false)
const experimentSubmitting = ref(false)
const resultSubmitting = ref(false)
const experimentDeleting = ref(false)
const busy = computed(() => experimentSubmitting.value || resultSubmitting.value || experimentDeleting.value)
const projectsError = ref('')
const batchesError = ref('')
const experimentsError = ref('')
const resultError = ref('')
let contextRequest = 0
let batchRequest = 0
let experimentRequest = 0
let resultRequest = 0

function clearResult(): void {
  resultRequest += 1
  result.value = null
  resultMissing.value = false
  resultError.value = ''
  resultLoading.value = false
}

function clearExperimentSelection(): void {
  selectedExperiment.value = null
  clearResult()
}

function clearExperiments(): void {
  experimentRequest += 1
  experiments.value = []
  experimentsError.value = ''
  experimentsLoading.value = false
  clearExperimentSelection()
}

function clearBatches(): void {
  batchRequest += 1
  batchId.value = null
  batches.value = []
  batchesError.value = ''
  batchesLoading.value = false
  clearExperiments()
}

async function loadBatches(): Promise<void> {
  const target = projectId.value
  if (target === null) return
  const request = ++batchRequest
  batchesLoading.value = true
  batchesError.value = ''
  try {
    const response = await getProjectBatches(target)
    if (request === batchRequest && projectId.value === target) batches.value = response
  } catch (error: unknown) {
    if (request === batchRequest && projectId.value === target) {
      batchesError.value = getApiErrorMessage(error, '批次列表加载失败，请重试。')
      ElMessage.error(batchesError.value)
    }
  } finally {
    if (request === batchRequest) batchesLoading.value = false
  }
}

async function loadExperiments(): Promise<void> {
  const target = batchId.value
  if (target === null) return
  const request = ++experimentRequest
  experimentsLoading.value = true
  experimentsError.value = ''
  try {
    const response = await getBatchExperiments(target)
    if (request !== experimentRequest || batchId.value !== target) return
    experiments.value = response
    if (selectedExperiment.value) {
      const current = response.find(experiment => experiment.id === selectedExperiment.value?.id)
      if (current) selectedExperiment.value = current
      else clearExperimentSelection()
    }
  } catch (error: unknown) {
    if (request === experimentRequest && batchId.value === target) {
      experimentsError.value = getApiErrorMessage(error, '实验列表加载失败，请重试。')
      ElMessage.error(experimentsError.value)
    }
  } finally {
    if (request === experimentRequest) experimentsLoading.value = false
  }
}

async function loadResult(): Promise<void> {
  const target = selectedExperiment.value?.id
  if (target === undefined) return
  clearResult()
  const request = ++resultRequest
  resultLoading.value = true
  try {
    const response = await getExperimentResult(target)
    if (request === resultRequest && selectedExperiment.value?.id === target) result.value = response
  } catch (error: unknown) {
    if (request !== resultRequest || selectedExperiment.value?.id !== target) return
    if (isApiErrorDetail(error, 'Experiment result not found', 404)) {
      resultMissing.value = true
    } else if (isApiErrorDetail(error, 'Experiment not found', 404)) {
      ElMessage.error(getApiErrorMessage(error))
      clearExperimentSelection()
      await loadExperiments()
    } else {
      resultError.value = getApiErrorMessage(error, '实验结果加载失败，请重试。')
      ElMessage.error(resultError.value)
    }
  } finally {
    if (request === resultRequest) resultLoading.value = false
  }
}

function selectProject(): void {
  contextRequest += 1
  clearBatches()
  void loadBatches()
}

function selectBatch(): void {
  contextRequest += 1
  clearExperiments()
  void loadExperiments()
}

function selectExperiment(experiment: Experiment): void {
  if (busy.value) return
  selectedExperiment.value = experiment
  void loadResult()
}

function queryId(value: unknown): number | null {
  if (typeof value !== 'string' || !/^[1-9]\d*$/.test(value)) return null
  const parsed = Number(value)
  return Number.isSafeInteger(parsed) ? parsed : null
}

async function initializeContext(): Promise<void> {
  const request = ++contextRequest
  projectId.value = null
  clearBatches()
  projectsLoading.value = true
  projectsError.value = ''
  try {
    const response = await getProjects()
    if (request !== contextRequest) return
    projects.value = response
    const requestedProject = queryId(route.query.projectId)
    const requestedBatch = queryId(route.query.batchId)
    if (requestedProject === null || requestedBatch === null || !response.some(project => project.id === requestedProject)) return
    projectId.value = requestedProject
    await loadBatches()
    if (request !== contextRequest) return
    if (!batches.value.some(batch => batch.id === requestedBatch && batch.project_id === requestedProject)) {
      projectId.value = null
      clearBatches()
      return
    }
    batchId.value = requestedBatch
    await loadExperiments()
  } catch (error: unknown) {
    if (request === contextRequest) {
      projectsError.value = getApiErrorMessage(error, '项目列表加载失败，请重试。')
      ElMessage.error(projectsError.value)
    }
  } finally {
    if (request === contextRequest) projectsLoading.value = false
  }
}

const experimentDialogVisible = ref(false)
const experimentEditingId = ref<number | null>(null)
const experimentBatchId = ref<number | null>(null)
const experimentFormRef = ref<FormInstance>()
const experimentForm = reactive({ experiment_no: '', model_name: '', parameters: '{}', notes: '' })

function parseParameters(text: string): Record<string, unknown> {
  let parsed: unknown
  try { parsed = JSON.parse(text) } catch { throw new Error('实验参数必须是合法的 JSON 对象。') }
  if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed) || Object.keys(parsed).length === 0) {
    throw new Error('实验参数必须是非空 JSON 对象。')
  }
  return parsed as Record<string, unknown>
}

const experimentRules: FormRules<typeof experimentForm> = {
  experiment_no: [{ required: true, trigger: 'blur', validator: (_rule, value: unknown, callback) => {
    callback(typeof value === 'string' && value.trim() ? undefined : new Error('实验编号不能为空'))
  } }],
  model_name: [{ required: true, trigger: 'blur', validator: (_rule, value: unknown, callback) => {
    callback(typeof value === 'string' && value.trim() ? undefined : new Error('模型名称不能为空'))
  } }],
  parameters: [{ required: true, trigger: 'blur', validator: (_rule, value: unknown, callback) => {
    try {
      if (typeof value !== 'string') throw new Error('实验参数必须是合法的 JSON 对象。')
      parseParameters(value)
      callback()
    } catch (error: unknown) { callback(error instanceof Error ? error : new Error('实验参数校验失败')) }
  } }],
}

async function openExperimentDialog(experiment?: Experiment): Promise<void> {
  if (busy.value || batchId.value === null) return
  experimentEditingId.value = experiment?.id ?? null
  experimentBatchId.value = batchId.value
  experimentForm.experiment_no = experiment?.experiment_no ?? ''
  experimentForm.model_name = experiment?.model_name ?? ''
  experimentForm.parameters = experiment ? JSON.stringify(experiment.parameters, null, 2) : '{}'
  experimentForm.notes = experiment?.notes ?? ''
  experimentDialogVisible.value = true
  await nextTick()
  experimentFormRef.value?.clearValidate()
}

async function submitExperiment(): Promise<void> {
  if (busy.value || !experimentFormRef.value || experimentBatchId.value === null) return
  experimentSubmitting.value = true
  const targetBatch = experimentBatchId.value
  const editingId = experimentEditingId.value
  try {
    if (!await experimentFormRef.value.validate().catch(() => false)) return
    const payload = {
      experiment_no: experimentForm.experiment_no.trim().toUpperCase(),
      model_name: experimentForm.model_name.trim(),
      parameters: parseParameters(experimentForm.parameters),
      notes: experimentForm.notes === '' ? null : experimentForm.notes,
    }
    const saved = editingId === null
      ? await createExperiment(targetBatch, payload) : await updateExperiment(editingId, payload)
    experimentDialogVisible.value = false
    ElMessage.success('实验已保存')
    if (batchId.value === targetBatch) {
      await loadExperiments()
      if (batchId.value === targetBatch && editingId === null) {
        selectedExperiment.value = saved
        await loadResult()
      }
    }
  } catch (error: unknown) { ElMessage.error(getApiErrorMessage(error)) }
  finally { experimentSubmitting.value = false }
}

async function removeExperiment(experiment: Experiment): Promise<void> {
  if (busy.value) return
  experimentDeleting.value = true
  try {
    await ElMessageBox.confirm(`确定删除实验“${experiment.experiment_no}”吗？删除实验后，其已有实验结果也会一并删除，此操作不可撤销。`, '删除确认', {
      confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning', distinguishCancelAndClose: true,
    })
    await deleteExperiment(experiment.id)
    if (selectedExperiment.value?.id === experiment.id) clearExperimentSelection()
    ElMessage.success('实验已删除')
    if (batchId.value === experiment.batch_id) await loadExperiments()
  } catch (error: unknown) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(getApiErrorMessage(error))
  } finally { experimentDeleting.value = false }
}

const metrics: { key: ResultMetric; label: string }[] = [
  { key: 'accuracy', label: 'Accuracy' }, { key: 'precision', label: 'Precision' },
  { key: 'recall', label: 'Recall' }, { key: 'f1', label: 'F1' }, { key: 'loss', label: 'Loss' },
]
const resultDialogVisible = ref(false)
const resultEditing = ref(false)
const resultExperimentId = ref<number | null>(null)
const resultFormRef = ref<FormInstance>()
const resultForm = reactive<Record<ResultMetric, string>>({ accuracy: '', precision: '', recall: '', f1: '', loss: '' })
const resultFormError = ref('')

function parseMetric(key: ResultMetric, text: string): number | null {
  if (text.trim() === '') return null
  const number = Number(text)
  if (!Number.isFinite(number)) throw new Error('请输入有限的数值')
  if (number < 0 || (key !== 'loss' && number > 1)) {
    throw new Error(key === 'loss' ? 'Loss 必须大于或等于 0' : '指标必须处于 [0, 1]')
  }
  return number
}

const resultRules: FormRules<typeof resultForm> = Object.fromEntries(metrics.map(metric => [metric.key, [{
  trigger: 'blur', validator: (_rule: unknown, value: unknown, callback: (error?: Error) => void) => {
    try {
      if (typeof value !== 'string') throw new Error('请输入有限的数值')
      parseMetric(metric.key, value)
      callback()
    } catch (error: unknown) { callback(error instanceof Error ? error : new Error('指标校验失败')) }
  },
}]]))

async function openResultDialog(): Promise<void> {
  if (busy.value || resultLoading.value || !selectedExperiment.value || (!result.value && !resultMissing.value)) return
  resultExperimentId.value = selectedExperiment.value.id
  resultEditing.value = result.value !== null
  for (const metric of metrics) {
    const value = result.value?.[metric.key]
    resultForm[metric.key] = value === null || value === undefined ? '' : String(value)
  }
  resultFormError.value = ''
  resultDialogVisible.value = true
  await nextTick()
  resultFormRef.value?.clearValidate()
}

async function submitResult(): Promise<void> {
  if (busy.value || !resultFormRef.value || resultExperimentId.value === null) return
  resultSubmitting.value = true
  const target = resultExperimentId.value
  const editing = resultEditing.value
  resultFormError.value = ''
  try {
    if (!await resultFormRef.value.validate().catch(() => false)) return
    const payload: ResultPayload = Object.fromEntries(metrics.map(metric => [metric.key, parseMetric(metric.key, resultForm[metric.key])]))
    if (Object.values(payload).every(value => value === null)) {
      resultFormError.value = '实验结果至少需要一个有效指标，0 也是合法值。'
      return
    }
    if (editing) await updateExperimentResult(target, payload)
    else await createExperimentResult(target, payload)
    resultDialogVisible.value = false
    ElMessage.success('实验结果已保存')
    if (selectedExperiment.value?.id === target) await loadResult()
  } catch (error: unknown) {
    ElMessage.error(getApiErrorMessage(error))
    if (isApiErrorDetail(error, 'Experiment result already exists', 409)
      || isApiErrorDetail(error, 'Experiment result not found', 404)
      || isApiErrorDetail(error, 'Experiment not found', 404)) {
      resultDialogVisible.value = false
      if (selectedExperiment.value?.id === target) await loadResult()
    }
  } finally { resultSubmitting.value = false }
}

watch(() => [route.query.projectId, route.query.batchId], () => { void initializeContext() }, { immediate: true })
onBeforeUnmount(() => { contextRequest += 1; batchRequest += 1; experimentRequest += 1; resultRequest += 1 })
</script>

<template>
  <section class="page-heading">
    <h1>实验管理</h1>
    <p>选择项目与批次，管理单次实验、实验参数和当前有效结果。</p>
  </section>

  <el-card shadow="never" class="management-card">
    <template #header>
      <div class="card-header"><h2>实验上下文</h2>
        <el-button :loading="projectsLoading" :disabled="busy || batchesLoading || experimentsLoading" @click="initializeContext">刷新项目</el-button>
      </div>
    </template>
    <el-alert v-if="projectsError" :title="projectsError" type="error" :closable="false" show-icon />
    <div class="context-selectors">
      <div><label for="experiment-project">实验项目</label>
        <el-select id="experiment-project" v-model="projectId" aria-label="实验项目" placeholder="请选择实验项目"
                   :loading="projectsLoading" :disabled="busy || projectsLoading" @change="selectProject">
          <el-option v-for="project in projects" :key="project.id" :label="project.name" :value="project.id" />
        </el-select>
      </div>
      <div><label for="experiment-batch">实验批次</label>
        <el-select id="experiment-batch" v-model="batchId" aria-label="实验批次" placeholder="请选择实验批次"
                   :loading="batchesLoading" :disabled="busy || !projectId || projectsLoading || batchesLoading" @change="selectBatch">
          <el-option v-for="batch in batches" :key="batch.id" :label="batch.name" :value="batch.id" />
        </el-select>
      </div>
    </div>
    <el-alert v-if="batchesError" :title="batchesError" type="error" :closable="false" show-icon />
    <p v-if="!projectId" class="hint">请先选择实验项目，再选择所属实验批次。</p>
    <el-empty v-else-if="!batchesLoading && !batchesError && batches.length === 0" description="当前项目暂无实验批次，请先前往项目管理创建批次。">
      <el-button @click="router.push('/projects')">前往项目管理</el-button>
    </el-empty>
  </el-card>

  <el-card shadow="never" class="management-card">
    <template #header>
      <div class="card-header">
        <h2>{{ selectedBatch ? `${selectedBatch.name} / 当前批次实验` : '当前批次实验' }}</h2>
        <div class="card-actions">
          <el-button :loading="experimentsLoading" :disabled="!batchId || busy" @click="loadExperiments">刷新实验</el-button>
          <el-button type="primary" :disabled="!batchId || busy || experimentsLoading" @click="openExperimentDialog()">新建实验</el-button>
        </div>
      </div>
    </template>
    <el-empty v-if="!batchId" description="请选择一个实验批次查看实验记录" />
    <el-alert v-else-if="experimentsError" :title="experimentsError" type="error" :closable="false" show-icon />
    <el-empty v-else-if="!experimentsLoading && experiments.length === 0" description="当前批次暂无实验记录">
      <el-button type="primary" :disabled="busy" @click="openExperimentDialog()">新建实验</el-button>
    </el-empty>
    <el-table v-else v-loading="experimentsLoading" :data="experiments" row-key="id" aria-label="实验记录列表">
      <el-table-column prop="experiment_no" label="实验编号" min-width="140" show-overflow-tooltip />
      <el-table-column prop="model_name" label="模型名称" min-width="150" show-overflow-tooltip />
      <el-table-column label="参数" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">{{ JSON.stringify(row.parameters) }}</template>
      </el-table-column>
      <el-table-column label="备注" min-width="120" show-overflow-tooltip><template #default="{ row }">{{ row.notes ?? '-' }}</template></el-table-column>
      <el-table-column label="创建时间" width="180"><template #default="{ row }">{{ formatDateTime(row.created_at) }}</template></el-table-column>
      <el-table-column label="操作" width="210">
        <template #default="{ row }">
          <el-button link type="primary" :disabled="busy || experimentsLoading" @click="selectExperiment(row)">查看结果</el-button>
          <el-button link type="primary" :disabled="busy || experimentsLoading" @click="openExperimentDialog(row)">编辑</el-button>
          <el-button link type="danger" :disabled="busy || experimentsLoading" @click="removeExperiment(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-card shadow="never" class="management-card">
    <template #header>
      <div class="card-header"><h2>{{ selectedExperiment ? `当前实验结果：${selectedExperiment.experiment_no}` : '当前实验结果' }}</h2>
        <el-button :loading="resultLoading" :disabled="!selectedExperiment || busy" @click="loadResult">刷新结果</el-button>
      </div>
    </template>
    <el-empty v-if="!selectedExperiment" description="请选择一个实验查看当前结果" />
    <div v-else v-loading="resultLoading" class="result-content">
      <el-alert v-if="resultError" :title="resultError" type="error" :closable="false" show-icon />
      <el-empty v-else-if="resultMissing" description="该实验尚未录入结果">
        <el-button type="primary" :disabled="busy || resultLoading" @click="openResultDialog">录入结果</el-button>
      </el-empty>
      <template v-else-if="result">
        <el-descriptions :column="2" border>
          <el-descriptions-item v-for="metric in metrics" :key="metric.key" :label="metric.label">{{ result[metric.key] === null ? '-' : result[metric.key] }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ formatDateTime(result.updated_at) }}</el-descriptions-item>
        </el-descriptions>
        <el-button class="edit-result" type="primary" :disabled="busy || resultLoading" @click="openResultDialog">编辑结果</el-button>
      </template>
    </div>
  </el-card>

  <el-dialog v-model="experimentDialogVisible" :title="experimentEditingId === null ? '新建实验' : '编辑实验'" width="min(600px, 92vw)"
             :close-on-click-modal="!experimentSubmitting" :close-on-press-escape="!experimentSubmitting" :show-close="!experimentSubmitting">
    <el-form ref="experimentFormRef" :model="experimentForm" :rules="experimentRules" label-position="top" :disabled="experimentSubmitting" @submit.prevent="submitExperiment">
      <el-form-item label="实验编号" prop="experiment_no"><el-input v-model="experimentForm.experiment_no" aria-label="实验编号" /></el-form-item>
      <el-form-item label="模型名称" prop="model_name"><el-input v-model="experimentForm.model_name" aria-label="模型名称" /></el-form-item>
      <el-form-item label="实验参数（JSON 对象）" prop="parameters"><el-input v-model="experimentForm.parameters" type="textarea" :rows="6" aria-label="实验参数" /></el-form-item>
      <el-form-item label="备注（可选）" prop="notes"><el-input v-model="experimentForm.notes" type="textarea" :rows="2" aria-label="备注" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button :disabled="experimentSubmitting" @click="experimentDialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="experimentSubmitting" :disabled="experimentSubmitting" @click="submitExperiment">保存实验</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="resultDialogVisible" :title="resultEditing ? '编辑实验结果' : '录入实验结果'" width="min(520px, 92vw)"
             :close-on-click-modal="!resultSubmitting" :close-on-press-escape="!resultSubmitting" :show-close="!resultSubmitting">
    <p class="hint">每项可以留空；至少填写一项。Accuracy、Precision、Recall、F1 范围为 [0, 1]，Loss ≥ 0。</p>
    <el-alert v-if="resultFormError" :title="resultFormError" type="error" :closable="false" show-icon />
    <el-form ref="resultFormRef" :model="resultForm" :rules="resultRules" label-position="top" :disabled="resultSubmitting" @submit.prevent="submitResult">
      <el-form-item v-for="metric in metrics" :key="metric.key" :label="metric.label" :prop="metric.key">
        <el-input v-model="resultForm[metric.key]" inputmode="decimal" :aria-label="metric.label" placeholder="留空表示无此指标" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button :disabled="resultSubmitting" @click="resultDialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="resultSubmitting" :disabled="resultSubmitting" @click="submitResult">保存结果</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.page-heading { margin-bottom: 28px; }
h1 { margin: 0 0 12px; font-size: 28px; }
.page-heading p, .hint { color: #6b7280; line-height: 1.7; }
.management-card { margin-bottom: 24px; }
.card-header { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 16px; }
h2 { margin: 0; font-size: 18px; overflow-wrap: anywhere; }
.card-actions { display: flex; flex-wrap: wrap; gap: 8px; }
.card-actions .el-button { margin-left: 0; }
.context-selectors { display: flex; flex-wrap: wrap; gap: 20px; margin: 16px 0; }
.context-selectors > div { flex: 1; min-width: 240px; }
.context-selectors label { display: block; margin-bottom: 8px; font-size: 14px; }
.context-selectors .el-select { width: 100%; }
.result-content { min-height: 120px; }
.edit-result { margin-top: 20px; }
</style>
