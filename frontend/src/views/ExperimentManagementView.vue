<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { getProjects } from '../api/projects'
import type { Project } from '../api/projects'
import { getProjectBatches } from '../api/batches'
import type { ExperimentBatch } from '../api/batches'
import { createExperiment, deleteExperiment, getProjectExperiments, updateExperiment } from '../api/experiments'
import type { Experiment } from '../api/experiments'
import { createExperimentResult, getExperimentResult, updateExperimentResult } from '../api/results'
import type { BuiltinMetric, ExperimentResult, ResultMetric, ResultPayload } from '../api/results'
import { getProjectMetrics, metricLabel } from '../api/metrics'
import type { MetricDefinition } from '../api/metrics'
import { getApiErrorMessage, isApiErrorDetail } from '../api/errors'
import { formatDateTime } from '../utils/datetime'
import BatchManager from '../components/BatchManager.vue'
import ProjectMetrics from '../components/ProjectMetrics.vue'
import { keepExistingSelection, setVisibleSelection } from '../utils/workspace-selection'
import ExperimentImport from '../components/ExperimentImport.vue'
import ResultJsonMapper from '../components/ResultJsonMapper.vue'
import { comparisonQuery } from '../utils/comparison-selection'
import { copyExperimentDraft } from '../utils/experiment-copy'

const route = useRoute()
const router = useRouter()
const projects = ref<Project[]>([])
const batches = ref<ExperimentBatch[]>([])
const experiments = ref<Experiment[]>([])
const checkedIds = ref<number[]>([])
const visibleExperiments = computed(() => batchId.value === null ? experiments.value : experiments.value.filter(item => item.batch_id === batchId.value))
const allVisibleChecked = computed(() => visibleExperiments.value.length > 0 && visibleExperiments.value.every(item => checkedIds.value.includes(item.id)))
const someVisibleChecked = computed(() => visibleExperiments.value.some(item => checkedIds.value.includes(item.id)) && !allVisibleChecked.value)
function toggleVisible(checked: boolean): void { checkedIds.value = setVisibleSelection(checkedIds.value, visibleExperiments.value.map(item => item.id), checked) }
function toggleExperiment(id: number, checked: boolean): void { checkedIds.value = setVisibleSelection(checkedIds.value, [id], checked) }
function compareChecked(): void {
  if (checkedIds.value.length < 2) return
  void router.push({ path: '/compare', query: comparisonQuery(checkedIds.value) })
}
const detailOpen = ref(false)
const batchManagerOpen = ref(false)
const metricManagerOpen = ref(false)
const settingsBusy = ref(false)
const selectedProject = computed(() => projects.value.find(item => item.id === projectId.value))
const contextError = ref('')
let loadedProjectId: number | null = null
function batchName(id: number): string { return batches.value.find(item => item.id === id)?.name ?? `批次 #${id}` }
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
const importBusy = ref(false)
const resultFileLoading = ref(false)
const busy = computed(() => experimentSubmitting.value || resultSubmitting.value || experimentDeleting.value || importBusy.value || resultFileLoading.value || settingsBusy.value)
const projectsError = ref('')
const batchesError = ref('')
const metricDefinitions = ref<MetricDefinition[]>([])
const metricsLoading = ref(false)
const metricsError = ref('')
let metricRequest = 0
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
  detailOpen.value = false
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
  metricRequest += 1
  metricDefinitions.value = []
  metricsError.value = ''
  metricsLoading.value = false
  batchRequest += 1
  batchId.value = null
  batches.value = []
  batchesError.value = ''
  batchesLoading.value = false
  clearExperiments()
}

async function loadMetricDefinitions(): Promise<void> {
  const target = projectId.value
  if (target === null) return
  const request = ++metricRequest
  metricsLoading.value = true
  metricsError.value = ''
  try {
    const response = await getProjectMetrics(target)
    if (request === metricRequest && projectId.value === target) metricDefinitions.value = response
  } catch (error: unknown) {
    if (request === metricRequest) metricsError.value = getApiErrorMessage(error, '项目指标加载失败，请刷新项目。')
  } finally { if (request === metricRequest) metricsLoading.value = false }
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
  const target = projectId.value
  if (target === null) return
  const request = ++experimentRequest
  experimentsLoading.value = true
  experimentsError.value = ''
  try {
    const response = await getProjectExperiments(target)
    if (request !== experimentRequest || projectId.value !== target) return
    experiments.value = response
    checkedIds.value = keepExistingSelection(checkedIds.value, response.map(item => item.id))
    if (selectedExperiment.value) {
      const current = response.find(experiment => experiment.id === selectedExperiment.value?.id)
      if (current) selectedExperiment.value = current
      else clearExperimentSelection()
    }
  } catch (error: unknown) {
    if (request === experimentRequest && projectId.value === target) {
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
  void router.push({ path: '/experiments', query: projectId.value === null ? {} : { projectId: projectId.value } })
}

function selectBatch(): void {
  void router.replace({ path: '/experiments', query: { projectId: String(projectId.value), ...(batchId.value === null ? {} : { batchId: String(batchId.value) }) } })
}

async function refreshBatches(): Promise<void> {
  await loadBatches()
  if (batchesError.value) return
  if (batchId.value !== null && !batches.value.some(item => item.id === batchId.value)) { batchId.value = null; selectBatch() }
  await loadExperiments()
}

function selectExperiment(experiment: Experiment): void {
  if (busy.value) return
  selectedExperiment.value = experiment
  detailOpen.value = true
  void loadResult()
}

function queryId(value: unknown): number | null {
  if (typeof value !== 'string' || !/^[1-9]\d*$/.test(value)) return null
  const parsed = Number(value)
  return Number.isSafeInteger(parsed) ? parsed : null
}

async function initializeContext(force = false): Promise<void> {
  const requestedProject = queryId(route.query.projectId)
  const requestedBatch = queryId(route.query.batchId)
  const request = ++contextRequest
  if (!force && !projectsLoading.value && requestedProject !== null && requestedProject === loadedProjectId && requestedProject === projectId.value) {
    batchId.value = requestedBatch !== null && batches.value.some(item => item.id === requestedBatch) ? requestedBatch : null
    contextError.value = route.query.batchId && batchId.value === null ? '指定批次不存在或不属于当前项目，已显示全部实验。' : ''
    return
  }
  if (requestedProject !== loadedProjectId || requestedProject !== projectId.value) { checkedIds.value = []; clearBatches() }
  projectsLoading.value = true
  projectsError.value = ''; contextError.value = ''
  try {
    const response = await getProjects()
    if (request !== contextRequest) return
    projects.value = response
    if (requestedProject === null || !response.some(item => item.id === requestedProject)) {
      projectId.value = null; loadedProjectId = null; clearBatches(); checkedIds.value = []
      if (route.query.projectId) contextError.value = '指定项目不存在，请重新选择项目。'
      return
    }
    projectId.value = requestedProject
    await Promise.all([loadBatches(), loadMetricDefinitions(), loadExperiments()])
    if (request !== contextRequest) return
    batchId.value = requestedBatch !== null && batches.value.some(item => item.id === requestedBatch) ? requestedBatch : null
    if (route.query.batchId && batchId.value === null) contextError.value = '指定批次不存在或不属于当前项目，已显示全部实验。'
    loadedProjectId = requestedProject
  } catch (error) {
    if (request === contextRequest) projectsError.value = getApiErrorMessage(error, '项目列表加载失败，请重试。')
  } finally { if (request === contextRequest) projectsLoading.value = false }
}

const experimentDialogVisible = ref(false)
const experimentEditingId = ref<number | null>(null)
const copyingFrom = ref('')
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
  if (busy.value || projectId.value === null || batches.value.length === 0) return
  copyingFrom.value = ''
  experimentEditingId.value = experiment?.id ?? null
  experimentBatchId.value = experiment?.batch_id ?? batchId.value
  experimentForm.experiment_no = experiment?.experiment_no ?? ''
  experimentForm.model_name = experiment?.model_name ?? ''
  experimentForm.parameters = experiment ? JSON.stringify(experiment.parameters, null, 2) : '{}'
  experimentForm.notes = experiment?.notes ?? ''
  experimentDialogVisible.value = true
  await nextTick()
  experimentFormRef.value?.clearValidate()
}

async function openCopyDialog(experiment: Experiment): Promise<void> {
  await openExperimentDialog()
  if (!experimentDialogVisible.value || busy.value) return
  copyingFrom.value = experiment.experiment_no
  Object.assign(experimentForm, copyExperimentDraft(experiment))
  experimentFormRef.value?.clearValidate()
}

async function submitExperiment(): Promise<void> {
  if (busy.value || !experimentFormRef.value) return
  if (experimentBatchId.value === null) { ElMessage.error('请选择实验所属批次'); return }
  experimentSubmitting.value = true
  const targetBatch = experimentBatchId.value
  const editingId = experimentEditingId.value
  try {
    if (!await experimentFormRef.value.validate().catch(() => false)) return
    if (!batches.value.some(batch => batch.id === targetBatch && batch.project_id === projectId.value)) {
      ElMessage.error('请选择当前项目内的有效目标批次')
      return
    }
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
    await loadExperiments()
    if (selectedExperiment.value?.id === saved.id) selectedExperiment.value = saved
    if (editingId === null) {
      selectedExperiment.value = saved
      detailOpen.value = true
      await loadResult()
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
    checkedIds.value = checkedIds.value.filter(id => id !== experiment.id)
    await loadExperiments()
  } catch (error: unknown) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(getApiErrorMessage(error))
  } finally { experimentDeleting.value = false }
}

const metrics = computed(() => metricDefinitions.value.map(definition => ({ ...definition,
  label: definition.builtin ? definition.name : metricLabel(definition) })))
const resultDialogVisible = ref(false)
const resultEditing = ref(false)
const resultExperimentId = ref<number | null>(null)
const resultFormRef = ref<FormInstance>()
const resultForm = reactive<Record<ResultMetric, string>>({ accuracy: '', precision: '', recall: '', f1: '', loss: '' })
const resultFormError = ref('')
const resultMappingBlocked = ref(false)
const resultMapperVersion = ref(0)

function parseMetric(key: ResultMetric, text: string): number | null {
  if (text.trim() === '') return null
  const number = Number(text)
  if (!Number.isFinite(number)) throw new Error('请输入有限的数值')
  const definition = metrics.value.find(metric => metric.key === key)
  if (!definition) throw new Error('项目指标已变化，请重新打开结果表单')
  if ((definition.lower_bound !== null && number < definition.lower_bound)
      || (definition.upper_bound !== null && number > definition.upper_bound)) {
    throw new Error(`指标必须处于 [${definition.lower_bound ?? '不限'}, ${definition.upper_bound ?? '不限'}]`)
  }
  return number
}

function applyResultMapping(values: Record<string, number | null>, replace: boolean): void {
  const fields: Record<string, string> = {}
  for (const metric of metrics.value) {
    if (replace || Object.hasOwn(values, metric.key)) {
      const value = values[metric.key]
      fields[metric.key] = value === null || value === undefined ? '' : String(value)
    }
  }
  Object.assign(resultForm, fields)
  resultFormError.value = ''
  resultFormRef.value?.clearValidate()
}

const resultRules = computed<FormRules<typeof resultForm>>(() => Object.fromEntries(metrics.value.map(metric => [metric.key, [{
  trigger: 'blur', validator: (_rule: unknown, value: unknown, callback: (error?: Error) => void) => {
    try {
      if (typeof value !== 'string') throw new Error('请输入有限的数值')
      parseMetric(metric.key, value)
      callback()
    } catch (error: unknown) { callback(error instanceof Error ? error : new Error('指标校验失败')) }
  },
}]])))

function resultMetricValue(metric: MetricDefinition): number | null {
  return metric.builtin ? result.value?.[metric.key as BuiltinMetric] ?? null : result.value?.custom_metrics?.[metric.key] ?? null
}

async function openResultDialog(): Promise<void> {
  if (busy.value || resultLoading.value || !selectedExperiment.value || (!result.value && !resultMissing.value)) return
  resultExperimentId.value = selectedExperiment.value.id
  resultEditing.value = result.value !== null
  await loadMetricDefinitions()
  if (metricsError.value || resultExperimentId.value !== selectedExperiment.value?.id) return
  for (const key of Object.keys(resultForm)) delete resultForm[key]
  for (const metric of metrics.value) {
    const value = resultMetricValue(metric)
    resultForm[metric.key] = value === null || value === undefined ? '' : String(value)
  }
  resultFormError.value = ''
  resultMappingBlocked.value = false
  resultMapperVersion.value += 1
  resultDialogVisible.value = true
  await nextTick()
  resultFormRef.value?.clearValidate()
}

async function submitResult(): Promise<void> {
  if (busy.value || !resultFormRef.value || resultExperimentId.value === null) return
  if (resultMappingBlocked.value) return
  resultSubmitting.value = true
  const target = resultExperimentId.value
  const editing = resultEditing.value
  resultFormError.value = ''
  try {
    if (!await resultFormRef.value.validate().catch(() => false)) return
    const values = Object.fromEntries(metrics.value.map(metric => [metric.key, parseMetric(metric.key, resultForm[metric.key] ?? '')]))
    if (Object.values(values).every(value => value === null)) {
      resultFormError.value = '实验结果至少需要一个有效指标，0 也是合法值。'
      return
    }
    const payload: ResultPayload = {
      accuracy: values.accuracy ?? null, precision: values.precision ?? null,
      recall: values.recall ?? null, f1: values.f1 ?? null, loss: values.loss ?? null,
      custom_metrics: Object.fromEntries(metrics.value.filter(metric => !metric.builtin).map(metric => [metric.key, values[metric.key] ?? null])),
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
onBeforeUnmount(() => { contextRequest += 1; batchRequest += 1; experimentRequest += 1; resultRequest += 1; metricRequest += 1 })
</script>

<template>
  <section class="page-heading">
    <h1>项目工作区</h1>
    <p v-if="selectedProject">{{ selectedProject.name }}</p>
  </section>

  <el-card shadow="never" class="management-card">
    <template #header>
      <div class="card-header"><h2>当前项目</h2>
        <el-button :loading="projectsLoading" :disabled="busy || batchesLoading || experimentsLoading" @click="initializeContext(true)">刷新工作区</el-button>
        <div class="card-actions"><el-button :disabled="!projectId || busy || projectsLoading" @click="batchManagerOpen = true">管理批次</el-button><el-button :disabled="!projectId || busy || projectsLoading" @click="metricManagerOpen = true">管理指标</el-button></div>
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
      <div><label for="experiment-batch">批次筛选</label>
        <el-select id="experiment-batch" v-model="batchId" aria-label="实验批次" clearable :value-on-clear="null" placeholder="全部批次"
                   :loading="batchesLoading" :disabled="busy || !projectId || projectsLoading || batchesLoading" @change="selectBatch">
          <el-option v-for="batch in batches" :key="batch.id" :label="batch.name" :value="batch.id" />
        </el-select>
      </div>
    </div>
    <el-alert v-if="contextError" :title="contextError" type="warning" :closable="false" show-icon />
    <el-alert v-if="batchesError" :title="batchesError" type="error" :closable="false" show-icon />
    <el-alert v-if="metricsError" :title="metricsError" type="error" :closable="false" show-icon />
    <el-empty v-if="!projectsLoading && !projectsError && projects.length === 0" description="暂无实验项目，请先前往项目管理创建项目。">
      <el-button @click="router.push('/projects')">前往项目管理</el-button>
    </el-empty>
    <p v-else-if="!projectId" class="hint">请选择实验项目。</p>
    <el-empty v-else-if="!batchesLoading && !batchesError && batches.length === 0" description="当前项目暂无实验批次。">
      <el-button @click="batchManagerOpen = true">新建批次</el-button>
    </el-empty>
  </el-card>

  <el-card shadow="never" class="management-card">
    <template #header>
      <div class="card-header">
        <h2>{{ selectedBatch ? selectedBatch.name : '全部批次' }} · 实验（{{ visibleExperiments.length }}）</h2>
        <div class="card-actions">
          <ExperimentImport :project-id="projectId" :batch-id="batchId" :batch-name="selectedBatch?.name" :batches="batches" :disabled="busy || experimentsLoading || projectsLoading" @busy="importBusy = $event" @imported="loadExperiments" />
          <el-button :disabled="busy || projectsLoading || experimentsLoading || checkedIds.length < 2" @click="compareChecked">比较所选实验（{{ checkedIds.length }}）</el-button>
          <el-button :loading="experimentsLoading" :disabled="!projectId || busy" @click="loadExperiments">刷新实验</el-button>
          <el-button type="primary" :disabled="!projectId || !batches.length || busy || projectsLoading || experimentsLoading" @click="openExperimentDialog()">新建实验</el-button>
        </div>
      </div>
    </template>
    <el-empty v-if="!projectId" description="请选择一个实验项目查看实验记录" />
    <el-alert v-else-if="experimentsError" :title="experimentsError" type="error" :closable="false" show-icon />
    <el-empty v-else-if="!experimentsLoading && visibleExperiments.length === 0" description="暂无实验记录">
      <el-button type="primary" :disabled="busy || !batches.length || projectsLoading" @click="openExperimentDialog()">新建实验</el-button>
    </el-empty>
    <el-table v-else v-loading="experimentsLoading" :data="visibleExperiments" row-key="id" aria-label="实验记录列表">
      <el-table-column width="48">
        <template #header><el-checkbox :model-value="allVisibleChecked" :indeterminate="someVisibleChecked" :disabled="busy || experimentsLoading" aria-label="选择当前列表全部实验" @change="toggleVisible(Boolean($event))" /></template>
        <template #default="{ row }"><el-checkbox :model-value="checkedIds.includes(row.id)" :disabled="busy || experimentsLoading" :aria-label="`选择实验 ${row.experiment_no}`" @change="toggleExperiment(row.id, Boolean($event))" /></template>
      </el-table-column>
      <el-table-column prop="experiment_no" label="实验编号" min-width="140" show-overflow-tooltip />
      <el-table-column label="批次" min-width="160" show-overflow-tooltip><template #default="{ row }">{{ batchName(row.batch_id) }}</template></el-table-column>
      <el-table-column prop="model_name" label="模型名称" min-width="150" show-overflow-tooltip />
      <el-table-column label="创建时间" width="180"><template #default="{ row }">{{ formatDateTime(row.created_at) }}</template></el-table-column>
      <el-table-column label="操作" width="290">
        <template #default="{ row }">
          <el-button link type="primary" :disabled="busy || experimentsLoading" @click="selectExperiment(row)">查看详情</el-button>
          <el-button link type="primary" :disabled="busy || experimentsLoading" @click="openExperimentDialog(row)">编辑</el-button>
          <el-button link type="primary" :disabled="busy || experimentsLoading" @click="openCopyDialog(row)">复制配置</el-button>
          <el-button link type="danger" :disabled="busy || experimentsLoading" @click="removeExperiment(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-drawer v-model="detailOpen" title="实验详情" size="min(760px, 96vw)" :close-on-click-modal="!busy" :close-on-press-escape="!busy" :show-close="!busy">
    <template v-if="selectedExperiment">
      <h2 class="detail-title">{{ selectedExperiment.experiment_no }}</h2>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="模型">{{ selectedExperiment.model_name }}</el-descriptions-item>
        <el-descriptions-item label="批次">{{ batchName(selectedExperiment.batch_id) }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDateTime(selectedExperiment.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="备注">{{ selectedExperiment.notes ?? '-' }}</el-descriptions-item>
      </el-descriptions>
      <h3>实验参数</h3><pre class="parameter-details">{{ JSON.stringify(selectedExperiment.parameters, null, 2) }}</pre>
      <div class="card-actions detail-actions">
        <el-button :disabled="busy" @click="openExperimentDialog(selectedExperiment)">编辑配置</el-button>
        <el-button :disabled="busy" @click="openCopyDialog(selectedExperiment)">复制配置</el-button>
        <el-button :loading="resultLoading" :disabled="busy" @click="loadResult">刷新结果</el-button>
      </div>
      <h3>当前实验结果</h3>
    </template>
    <div v-if="selectedExperiment" v-loading="resultLoading" class="result-content">
      <el-alert v-if="resultError" :title="resultError" type="error" :closable="false" show-icon />
      <el-empty v-else-if="resultMissing" description="该实验尚未录入结果">
        <el-button type="primary" :disabled="busy || resultLoading || metricsLoading" @click="openResultDialog">录入结果</el-button>
      </el-empty>
      <template v-else-if="result">
        <el-descriptions :column="2" border>
          <el-descriptions-item v-for="metric in metrics" :key="metric.key" :label="metric.label">{{ resultMetricValue(metric) ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ formatDateTime(result.updated_at) }}</el-descriptions-item>
        </el-descriptions>
        <el-button class="edit-result" type="primary" :disabled="busy || resultLoading || metricsLoading" @click="openResultDialog">编辑结果</el-button>
      </template>
    </div>
  </el-drawer>

  <el-dialog v-model="batchManagerOpen" title="管理批次" width="min(900px, 94vw)" :close-on-click-modal="!settingsBusy" :close-on-press-escape="!settingsBusy" :show-close="!settingsBusy">
    <BatchManager v-if="batchManagerOpen && projectId" :project-id="projectId" :batches="batches" :loading="batchesLoading" :error="batchesError" @changed="refreshBatches" @refresh="refreshBatches" @busy="settingsBusy = $event" />
  </el-dialog>
  <el-dialog v-model="metricManagerOpen" title="管理项目指标" width="min(1100px, 96vw)" :close-on-click-modal="!settingsBusy" :close-on-press-escape="!settingsBusy" :show-close="!settingsBusy" @closed="loadMetricDefinitions">
    <ProjectMetrics v-if="metricManagerOpen" :project-id="projectId" :project-name="selectedProject?.name" @busy="settingsBusy = $event" />
  </el-dialog>

  <el-dialog v-model="experimentDialogVisible" :title="copyingFrom ? '复制实验配置' : experimentEditingId === null ? '新建实验' : '编辑实验'" width="min(600px, 92vw)"
             :close-on-click-modal="!experimentSubmitting" :close-on-press-escape="!experimentSubmitting" :show-close="!experimentSubmitting">
    <el-form ref="experimentFormRef" :model="experimentForm" :rules="experimentRules" label-position="top" :disabled="experimentSubmitting" @submit.prevent="submitExperiment">
      <template v-if="copyingFrom">
        <el-alert :title="`来自 ${copyingFrom}，请填写新编号。实验结果不会复制。`" type="info" :closable="false" />
      </template>
      <el-form-item v-if="experimentEditingId === null" label="所属批次（必选）" required>
          <el-select v-model="experimentBatchId" aria-label="实验所属批次" placeholder="请选择所属批次">
            <el-option v-for="batch in batches" :key="batch.id" :label="batch.name" :value="batch.id" />
          </el-select>
      </el-form-item>
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

  <el-dialog v-model="resultDialogVisible" class="aiexphub-result-dialog" :title="resultEditing ? '编辑实验结果' : '录入实验结果'" width="min(780px, 94vw)" top="4vh"
             :close-on-click-modal="!busy" :close-on-press-escape="!busy" :show-close="!busy">
    <p class="hint">每项可留空，至少填写一项。系统指标保留原范围；自定义指标遵循项目配置的单位和上下限。</p>
    <ResultJsonMapper v-if="resultDialogVisible" :key="resultMapperVersion" :project-id="projectId ?? 0" :metrics="metricDefinitions" :disabled="resultSubmitting"
                      @applied="applyResultMapping" @blocked="resultMappingBlocked = $event" @reading="resultFileLoading = $event" />
    <el-alert v-if="resultFormError" :title="resultFormError" type="error" :closable="false" show-icon />
    <el-form ref="resultFormRef" class="result-metric-form" :model="resultForm" :rules="resultRules" label-position="top" :disabled="busy" @submit.prevent="submitResult">
      <el-form-item v-for="metric in metrics" :key="metric.key" :label="metric.label" :prop="metric.key">
        <p class="metric-hint">{{ metric.key }} · {{ metric.direction === 'max' ? '越大越好' : '越小越好' }} · {{ metric.lower_bound ?? '不限' }} ～ {{ metric.upper_bound ?? '不限' }}</p>
        <el-input v-model="resultForm[metric.key]" inputmode="decimal" :aria-label="metric.label" placeholder="留空表示无此指标" />
      </el-form-item>
    </el-form>
    <template #footer>
        <el-button :disabled="busy" @click="resultDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="resultSubmitting || resultFileLoading" :disabled="busy || resultMappingBlocked" @click="submitResult">保存结果</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.detail-title { overflow-wrap: anywhere; }
.parameter-details { white-space: pre-wrap; overflow-wrap: anywhere; background: #f5f7fa; padding: 16px; border-radius: 6px; }
.detail-actions { margin-top: 20px; }
.hint { color: #6b7280; line-height: 1.7; }
.result-content { min-height: 120px; }
.edit-result { margin-top: 20px; }
.result-metric-form { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 16px; }
.metric-hint { margin: 0 0 4px; color: #6b7280; font-size: 12px; width: 100%; }
@media (max-width: 480px) {
  .result-metric-form { grid-template-columns: minmax(0, 1fr); }
}
</style>

<style>
/* The dialog is teleported outside this view; keep this rule scoped by its class. */
.aiexphub-result-dialog .el-dialog__body { max-height: 70vh; overflow-y: auto; padding-right: 6px; }
</style>
