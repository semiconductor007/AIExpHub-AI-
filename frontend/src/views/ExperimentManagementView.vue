<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getProjects } from '../api/projects'
import type { Project } from '../api/projects'
import { getProjectBatches } from '../api/batches'
import type { ExperimentBatch } from '../api/batches'
import { createExperiment, deleteExperiment, getProjectExperiments, updateExperiment } from '../api/experiments'
import type { Experiment } from '../api/experiments'
import { createExperimentResult, getExperimentResult, updateExperimentResult } from '../api/results'
import type { BuiltinMetric, ExperimentResult } from '../api/results'
import { getProjectMetrics, metricLabel } from '../api/metrics'
import type { MetricDefinition } from '../api/metrics'
import { getApiErrorMessage, isApiErrorDetail } from '../api/errors'
import { formatDateTime } from '../utils/datetime'
import BatchManager from '../components/BatchManager.vue'
import ProjectMetrics from '../components/ProjectMetrics.vue'
import { keepExistingSelection, setVisibleSelection } from '../utils/workspace-selection'
import ExperimentImport from '../components/ExperimentImport.vue'
import ExperimentFormDialog, { type ExperimentDraft } from '../components/ExperimentFormDialog.vue'
import ExperimentResultDialog, { type ExperimentResultDraft } from '../components/ExperimentResultDialog.vue'
import { comparisonQuery } from '../utils/comparison-selection'

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
const batchSetupOpen = ref(false)
let setupProjectId: number | null = null
let handlingEntry = false
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
const metrics = computed(() => metricDefinitions.value)
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
  const action = route.query.action
  void router.push({ path: '/experiments', query: { ...(projectId.value === null ? {} : { projectId: projectId.value }), ...(action === 'new-experiment' || action === 'manage-batches' ? { action } : {}) } })
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

const experimentDialogRef = ref<InstanceType<typeof ExperimentFormDialog>>()
const resultDialogRef = ref<InstanceType<typeof ExperimentResultDialog>>()

function openExperimentDialog(experiment?: Experiment, targetBatchId?: number | null): Promise<void> {
  if (busy.value || projectId.value === null || batches.value.length === 0) return Promise.resolve()
  return experimentDialogRef.value?.open(experiment, { batchId: targetBatchId ?? batchId.value }) ?? Promise.resolve()
}

function openCopyDialog(experiment: Experiment): void {
  if (busy.value || projectId.value === null || batches.value.length === 0) return
  void experimentDialogRef.value?.open(experiment, { copyingFrom: experiment.experiment_no, batchId: batchId.value })
}

async function submitExperiment(draft: ExperimentDraft): Promise<void> {
  if (busy.value) return
  experimentSubmitting.value = true
  const targetBatch = draft.batchId
  const editingId = draft.editingId
  try {
    if (!batches.value.some(batch => batch.id === targetBatch && batch.project_id === projectId.value)) {
      ElMessage.error('请选择当前项目内的有效目标批次')
      return
    }
    const saved = editingId === null
      ? await createExperiment(targetBatch, draft.payload) : await updateExperiment(editingId, draft.payload)
    experimentDialogRef.value?.close()
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

function resultMetricValue(metric: MetricDefinition): number | null {
  return metric.builtin ? result.value?.[metric.key as BuiltinMetric] ?? null : result.value?.custom_metrics?.[metric.key] ?? null
}

async function openResultDialog(): Promise<void> {
  if (busy.value || resultLoading.value || !selectedExperiment.value || (!result.value && !resultMissing.value)) return
  const target = selectedExperiment.value.id
  await loadMetricDefinitions()
  if (metricsError.value || !projectId.value || selectedExperiment.value?.id !== target) return
  await resultDialogRef.value?.open(target, result.value)
}

async function submitResult(draft: ExperimentResultDraft): Promise<void> {
  if (busy.value) return
  resultSubmitting.value = true
  const target = draft.experimentId
  try {
    if (draft.editing) await updateExperimentResult(target, draft.payload)
    else await createExperimentResult(target, draft.payload)
    resultDialogRef.value?.close()
    ElMessage.success('实验结果已保存')
    if (selectedExperiment.value?.id === target) await loadResult()
  } catch (error: unknown) {
    ElMessage.error(getApiErrorMessage(error))
    if (isApiErrorDetail(error, 'Experiment result already exists', 409)
      || isApiErrorDetail(error, 'Experiment result not found', 404)
      || isApiErrorDetail(error, 'Experiment not found', 404)) {
      resultDialogRef.value?.close()
      if (selectedExperiment.value?.id === target) await loadResult()
    }
  } finally { resultSubmitting.value = false }
}

async function handleEntry(): Promise<void> {
  const action = route.query.action
  const target = projectId.value
  if (handlingEntry || (action !== 'new-experiment' && action !== 'manage-batches') || target === null
    || target !== queryId(route.query.projectId) || loadedProjectId !== target
    || projectsLoading.value || batchesLoading.value || projectsError.value || batchesError.value || busy.value) return
  handlingEntry = true
  try {
    const query = { ...route.query }; delete query.action
    await router.replace({ path: route.path, query })
    if (projectId.value !== target) return
    if (action === 'manage-batches') { batchManagerOpen.value = true; return }
    if (!batches.value.length) { setupProjectId = target; batchSetupOpen.value = true; return }
    await openExperimentDialog()
  } finally { handlingEntry = false }
}

async function continueAfterBatch(batch: ExperimentBatch): Promise<void> {
  const target = setupProjectId
  batchSetupOpen.value = false
  await nextTick()
  if (target === null || target !== projectId.value || batch.project_id !== target) return
  // BatchManager finishes its save before the experiment form is opened.
  await refreshBatches()
  if (projectId.value !== target || batchesError.value || busy.value) return
  await openExperimentDialog(undefined, batch.id)
}

watch(() => [route.query.projectId, route.query.batchId], () => { batchSetupOpen.value = false; setupProjectId = null; void initializeContext() }, { immediate: true })
watch(() => [route.query.action, projectsLoading.value, batchesLoading.value, busy.value, projectId.value], () => { void handleEntry() }, { flush: 'post', immediate: true })
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
        <div class="workspace-secondary-actions">
          <el-button :loading="projectsLoading" :disabled="busy || batchesLoading || experimentsLoading" @click="initializeContext(true)">刷新工作区</el-button>
          <el-button :disabled="!projectId || busy || projectsLoading" @click="batchManagerOpen = true">管理批次</el-button>
          <el-button :disabled="!projectId || busy || projectsLoading" @click="metricManagerOpen = true">管理指标</el-button>
        </div>
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
      <el-button @click="router.push({ path: '/projects', query: { action: 'create', ...(route.query.action === 'new-experiment' || route.query.action === 'manage-batches' ? { next: route.query.action } : {}) } })">创建项目</el-button>
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
        <div class="card-actions workspace-card-actions">
          <div class="workspace-primary-actions">
            <el-button type="primary" :disabled="!projectId || !batches.length || busy || projectsLoading || experimentsLoading" @click="openExperimentDialog()">新建实验</el-button>
            <el-button :disabled="busy || projectsLoading || experimentsLoading || checkedIds.length < 2" @click="compareChecked">比较所选实验（{{ checkedIds.length }}）</el-button>
          </div>
          <div class="workspace-secondary-actions">
            <ExperimentImport :project-id="projectId" :batch-id="batchId" :batch-name="selectedBatch?.name" :batches="batches" :disabled="busy || experimentsLoading || projectsLoading" @busy="importBusy = $event" @imported="loadExperiments" />
            <el-button :loading="experimentsLoading" :disabled="!projectId || busy" @click="loadExperiments">刷新实验</el-button>
          </div>
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
          <el-descriptions-item v-for="metric in metrics" :key="metric.key" :label="metricLabel(metric)">{{ resultMetricValue(metric) ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ formatDateTime(result.updated_at) }}</el-descriptions-item>
        </el-descriptions>
        <el-button class="edit-result" type="primary" :disabled="busy || resultLoading || metricsLoading" @click="openResultDialog">编辑结果</el-button>
      </template>
    </div>
  </el-drawer>

  <BatchManager v-if="batchSetupOpen && projectId" :project-id="projectId" :batches="batches" create-on-open @created="continueAfterBatch" @cancelled="batchSetupOpen = false" @busy="settingsBusy = $event" />
  <el-dialog v-model="batchManagerOpen" title="管理批次" width="min(900px, 94vw)" :close-on-click-modal="!settingsBusy" :close-on-press-escape="!settingsBusy" :show-close="!settingsBusy">
    <BatchManager v-if="batchManagerOpen && projectId" :project-id="projectId" :batches="batches" :loading="batchesLoading" :error="batchesError" @changed="refreshBatches" @refresh="refreshBatches" @busy="settingsBusy = $event" />
  </el-dialog>
  <el-dialog v-model="metricManagerOpen" title="管理项目指标" width="min(1100px, 96vw)" :close-on-click-modal="!settingsBusy" :close-on-press-escape="!settingsBusy" :show-close="!settingsBusy" @closed="loadMetricDefinitions">
    <ProjectMetrics v-if="metricManagerOpen" :project-id="projectId" :project-name="selectedProject?.name" @busy="settingsBusy = $event" />
  </el-dialog>

  <ExperimentFormDialog ref="experimentDialogRef" :batches="batches" :submitting="experimentSubmitting" @save="submitExperiment" />
  <ExperimentResultDialog v-if="projectId !== null" ref="resultDialogRef" :project-id="projectId" :metrics="metrics"
                          :submitting="resultSubmitting" @save="submitResult" @reading="resultFileLoading = $event" />
</template>

<style scoped>
.detail-title { overflow-wrap: anywhere; }
.parameter-details { white-space: pre-wrap; overflow-wrap: anywhere; background: #f5f7fa; padding: 16px; border-radius: 6px; }
.detail-actions { margin-top: 20px; }
.result-content { min-height: 120px; }
.edit-result { margin-top: 20px; }
.workspace-card-actions { flex: 1; justify-content: flex-end; }
.workspace-primary-actions, .workspace-secondary-actions { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.workspace-secondary-actions { padding-left: 12px; border-left: 1px solid #e5e7eb; }
@media (max-width: 480px) {
  .result-metric-form { grid-template-columns: minmax(0, 1fr); }
  .workspace-card-actions { width: 100%; justify-content: flex-start; }
  .workspace-secondary-actions { padding-left: 0; border-left: 0; }
}
</style>
