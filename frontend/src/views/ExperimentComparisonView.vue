<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { isAxiosError } from 'axios'
import { getProjects } from '../api/projects'
import type { Project } from '../api/projects'
import { getBatch, getProjectBatches } from '../api/batches'
import type { ExperimentBatch } from '../api/batches'
import { getExperiment, getBatchExperiments } from '../api/experiments'
import type { Experiment } from '../api/experiments'
import { compareExperiments } from '../api/compare'
import type { ComparisonExperiment, ExperimentCompareResponse, MetricName } from '../api/compare'
import { getApiErrorMessage } from '../api/errors'
import ComparisonCharts from '../components/ComparisonCharts.vue'
import CustomMetricChart from '../components/CustomMetricChart.vue'
import { metricLabel } from '../api/metrics'
import type { CustomMetricComparison } from '../api/compare'
import MetricDeltaDisplay from '../components/MetricDeltaDisplay.vue'
import AiExperimentSummary from '../components/AiExperimentSummary.vue'
import { affectsComparison, subscribeComparisonChanges } from '../utils/comparison-changes'
import type { ComparisonChange } from '../utils/comparison-changes'
import { createComparisonRefresh } from '../utils/comparison-refresh'
import { buildComparisonCsv, createExportSnapshot, exportFilename, runComparisonExport } from '../utils/comparison-export'
import { downloadBlob } from '../utils/download'
import { createChartPng } from '../utils/chart-image'
import type { ChartExportSpec, ChartExportTarget } from '../utils/chart-export-layout'

import { comparisonIds, comparisonQuery } from '../utils/comparison-selection'

interface SelectedExperiment {
  missing?: boolean
  id: number
  experiment_no: string
  model_name: string
  project_id: number
  project_name: string
  batch_id: number
  batch_name: string
}

const router = useRouter()
const route = useRoute()
const candidateOpen = ref(false)
const restoring = ref(false)
let restoreRequest = 0
const projects = ref<Project[]>([])
const batches = ref<ExperimentBatch[]>([])
const experiments = ref<Experiment[]>([])
const projectId = ref<number | null>(null)
const batchId = ref<number | null>(null)
const selectedProject = computed(() => projects.value.find(project => project.id === projectId.value))
const selectedBatch = computed(() => batches.value.find(batch => batch.id === batchId.value))
// Only candidate data follows the current project / batch; selections survive context changes.
const selectedExperiments = ref<SelectedExperiment[]>([])
const selectedById = computed(() => new Map(selectedExperiments.value.map(experiment => [experiment.id, experiment])))
const comparisonResult = ref<ExperimentCompareResponse | null>(null)
const baselineId = ref<number | null>(null)
const baselineExperiment = computed(() => comparisonResult.value?.experiments.find(item => item.id === comparisonResult.value?.baseline_comparison?.baseline_experiment_id))
const deltaMetrics = computed(() => new Map((comparisonResult.value?.baseline_comparison?.metrics ?? []).map(metric => [`${metric.project_id ?? 'system'}:${metric.key}`, metric])))
const isCrossProject = computed(() => new Set(comparisonResult.value?.experiments.map(item => item.project_id)).size > 1)
const projectsLoading = ref(false)
const batchesLoading = ref(false)
const experimentsLoading = ref(false)
const compareLoading = ref(false)
const exporting = ref(false)
const comparisonBusy = computed(() => compareLoading.value || exporting.value || restoring.value)
const exportError = ref('')
const builtinCharts = ref<InstanceType<typeof ComparisonCharts> | null>(null)
const customCharts = ref<InstanceType<typeof CustomMetricChart>[]>([])
let exportVersion = 0
let disposed = false
const projectsError = ref('')
const batchesError = ref('')
const experimentsError = ref('')
const compareError = ref('')
const comparisonStarted = ref(false)
const dataStale = ref(false)
const lastUpdated = ref<number | null>(null)
const comparisonHelpOpen = ref(false)
const refreshingAutomatically = ref(false)
let compareAbort: AbortController | undefined
let unsubscribeChanges: (() => void) | undefined
const autoRefresh = createComparisonRefresh({
  enabled: () => comparisonStarted.value && selectedExperiments.value.length >= 2,
  visible: () => document.visibilityState === 'visible',
  busy: () => comparisonBusy.value,
  refresh: async () => { await refreshComparison(true) },
})
const syncStatus = computed(() => {
  if (compareLoading.value) return refreshingAutomatically.value ? '正在自动获取最新比较结果…' : '正在获取比较结果…'
  if (comparisonResult.value && dataStale.value) return '下方显示上次成功获取的结果，当前数据尚未确认最新。'
  return ''
})
const lastUpdatedLabel = computed(() => lastUpdated.value === null ? '尚未获取' : new Date(lastUpdated.value).toLocaleTimeString('zh-CN', { hour12: false }))
let projectRequest = 0
let batchRequest = 0
let experimentRequest = 0
let compareRequest = 0
const metrics: { key: MetricName; label: string }[] = [
  { key: 'accuracy', label: 'Accuracy' }, { key: 'precision', label: 'Precision' },
  { key: 'recall', label: 'Recall' }, { key: 'f1', label: 'F1' }, { key: 'loss', label: 'Loss' },
]
const showBuiltinCharts = computed(() => !comparisonResult.value?.custom_metrics?.length
  || comparisonResult.value.experiments.some(experiment => metrics.some(metric => experiment.result?.[metric.key] != null)))

function clearCandidates(): void {
  experimentRequest += 1
  experiments.value = []
  experimentsError.value = ''
  experimentsLoading.value = false
}

function clearBatches(): void {
  batchRequest += 1
  batchId.value = null
  batches.value = []
  batchesError.value = ''
  batchesLoading.value = false
  clearCandidates()
}

async function loadProjects(): Promise<void> {
  if (projectsLoading.value) return
  const request = ++projectRequest
  projectsLoading.value = true
  projectsError.value = ''
  try {
    const response = await getProjects()
    if (request !== projectRequest) return
    projects.value = response
    if (projectId.value !== null && !response.some(project => project.id === projectId.value)) {
      projectId.value = null
      clearBatches()
    }
  } catch (error: unknown) {
    if (request === projectRequest) {
      projectsError.value = getApiErrorMessage(error, '项目列表加载失败，请重试。')
      ElMessage.error(projectsError.value)
    }
  } finally { if (request === projectRequest) projectsLoading.value = false }
}

async function loadBatches(): Promise<void> {
  const target = projectId.value
  if (target === null) return
  const request = ++batchRequest
  batchesLoading.value = true
  batchesError.value = ''
  try {
    const response = await getProjectBatches(target)
    if (request !== batchRequest || projectId.value !== target) return
    batches.value = response
    if (batchId.value !== null && !response.some(batch => batch.id === batchId.value)) {
      batchId.value = null
      clearCandidates()
    }
  } catch (error: unknown) {
    if (request === batchRequest && projectId.value === target) {
      batchesError.value = getApiErrorMessage(error, '批次列表加载失败，请重试。')
      ElMessage.error(batchesError.value)
    }
  } finally { if (request === batchRequest) batchesLoading.value = false }
}

async function loadExperiments(): Promise<void> {
  const target = batchId.value
  if (target === null) return
  const request = ++experimentRequest
  experimentsLoading.value = true
  experimentsError.value = ''
  try {
    const response = await getBatchExperiments(target)
    if (request === experimentRequest && batchId.value === target) experiments.value = response
  } catch (error: unknown) {
    if (request === experimentRequest && batchId.value === target) {
      experimentsError.value = getApiErrorMessage(error, '候选实验加载失败，请重试。')
      ElMessage.error(experimentsError.value)
    }
  } finally { if (request === experimentRequest) experimentsLoading.value = false }
}

function selectProject(): void {
  clearBatches()
  void loadBatches()
}

function selectBatch(): void {
  clearCandidates()
  void loadExperiments()
}

function clearComparison(): void {
  exportVersion += 1
  exportError.value = ''
  compareRequest += 1
  compareAbort?.abort()
  compareLoading.value = false
  autoRefresh.clear()
  comparisonStarted.value = false
  dataStale.value = false
  lastUpdated.value = null
  comparisonResult.value = null
  compareError.value = ''
}

watch(baselineId, () => { clearComparison(); saveSelection() }, { flush: 'sync' })

function deltaValue(experimentId: number, key: string, project: number | null = null) {
  return deltaMetrics.value.get(`${project ?? 'system'}:${key}`)?.comparisons[experimentId]
}

function addExperiment(experiment: Experiment): void {
  if (comparisonBusy.value || selectedById.value.has(experiment.id) || !selectedProject.value || !selectedBatch.value) return
  if (experiment.batch_id !== selectedBatch.value.id) return
  selectedExperiments.value.push({
    id: experiment.id, experiment_no: experiment.experiment_no, model_name: experiment.model_name,
    project_id: selectedProject.value.id, project_name: selectedProject.value.name,
    batch_id: selectedBatch.value.id, batch_name: selectedBatch.value.name,
  })
  clearComparison()
  saveSelection()
}

function removeExperiment(id: number): void {
  if (comparisonBusy.value) return
  selectedExperiments.value = selectedExperiments.value.filter(experiment => experiment.id !== id)
  if (baselineId.value === id) baselineId.value = null
  clearComparison()
  saveSelection()
}

function clearSelection(): void {
  if (comparisonBusy.value) return
  selectedExperiments.value = []
  baselineId.value = null
  clearComparison()
  saveSelection()
}

function saveSelection(): void {
  if (restoring.value || disposed) return
  void router.replace({ query: comparisonQuery(selectedExperiments.value.map(item => item.id), baselineId.value) })
}

async function restoreSelection(): Promise<void> {
  const request = ++restoreRequest
  let ids: number[]
  try { ids = comparisonIds(route.query.ids) }
  catch (error) { clearComparison(); compareError.value = (error as Error).message; return }
  const baseline = typeof route.query.baseline === 'string' && /^[1-9]\d*$/.test(route.query.baseline)
    && ids.includes(Number(route.query.baseline)) ? Number(route.query.baseline) : null
  if (ids.join(',') === selectedExperiments.value.map(item => item.id).join(',') && baseline === baselineId.value) return
  clearComparison()
  restoring.value = true
  try {
    const projectList = await getProjects()
    if (request !== restoreRequest) return
    projects.value = projectList
    const batchCache = new Map<number, Promise<ExperimentBatch>>()
    const restored = await Promise.all(ids.map(async id => {
      let experiment: Experiment
      try { experiment = await getExperiment(id) }
      catch (error) {
        if (!isAxiosError(error) || error.response?.status !== 404) throw error
        return { id, experiment_no: `实验 #${id}（已不存在）`, model_name: '', project_id: 0,
          project_name: '', batch_id: 0, batch_name: '', missing: true }
      }
      if (!batchCache.has(experiment.batch_id)) batchCache.set(experiment.batch_id, getBatch(experiment.batch_id))
      const batch = await batchCache.get(experiment.batch_id)!
      return { id, experiment_no: experiment.experiment_no, model_name: experiment.model_name,
        project_id: batch.project_id, project_name: projectList.find(item => item.id === batch.project_id)?.name ?? `项目 #${batch.project_id}`,
        batch_id: batch.id, batch_name: batch.name }
    }))
    if (request !== restoreRequest) return
    selectedExperiments.value = restored
    baselineId.value = baseline
    if (restored.some(item => item.missing)) compareError.value = '部分已选实验已不存在，请移除后重新比较。'
    else if (ids.length >= 2) await refreshComparison(false)
  } catch (error) {
    if (request === restoreRequest) compareError.value = getApiErrorMessage(error, '已选实验加载失败，请刷新页面重试。')
  } finally { if (request === restoreRequest) restoring.value = false }
}

watch(() => [route.query.ids, route.query.baseline], () => { void restoreSelection() }, { immediate: true })

function startComparison(): void { void refreshComparison(false) }

async function refreshComparison(automatic: boolean): Promise<boolean> {
  if (compareLoading.value || selectedExperiments.value.length < 2) return false
  if (automatic && (!comparisonStarted.value || exporting.value)) return false
  if (!automatic) autoRefresh.clear()
  comparisonStarted.value = true
  const request = ++compareRequest
  const ids = selectedExperiments.value.map(experiment => experiment.id)
  const baseline = baselineId.value
  const controller = new AbortController()
  compareAbort = controller
  refreshingAutomatically.value = automatic
  compareLoading.value = true
  compareError.value = ''
  try {
    const response = await compareExperiments(ids, baseline, controller.signal)
    if (request !== compareRequest) return false
    comparisonResult.value = response
    lastUpdated.value = Date.now()
    dataStale.value = autoRefresh.hasPending()
    for (const selected of selectedExperiments.value) {
      const latest = response.experiments.find(item => item.id === selected.id)
      if (latest) { selected.experiment_no = latest.experiment_no; selected.model_name = latest.model_name }
    }
    return true
  } catch (error: unknown) {
    if (request !== compareRequest || controller.signal.aborted) return false
    const missing = isAxiosError(error) && error.response?.status === 404
    if (missing) {
      comparisonResult.value = null
      lastUpdated.value = null
      comparisonStarted.value = false
      autoRefresh.clear()
    }
    dataStale.value = true
    const detail = getApiErrorMessage(error, '实验比较失败，请重试。')
    compareError.value = comparisonResult.value
      ? `更新失败，当前显示上次成功数据。${detail} 可点击“重新比较”重试。`
      : detail
    if (!automatic) ElMessage.error(compareError.value)
    return false
  } finally {
    if (request === compareRequest) {
      compareLoading.value = false
      compareAbort = undefined
      autoRefresh.settle()
    }
  }
}

async function exportComparison(target?: ChartExportTarget): Promise<void> {
  if (comparisonBusy.value || !comparisonResult.value) return
  const version = ++exportVersion
  exporting.value = true
  exportError.value = ''
  try {
    const saved = await runComparisonExport({
      isCurrent: () => !disposed && version === exportVersion,
      refresh: async () => {
        const refreshed = await refreshComparison(false)
        if (!refreshed || !comparisonResult.value || lastUpdated.value === null) {
          if (!disposed) exportError.value = '导出前刷新未成功，未生成文件。请处理上方提示后重试。'
          return null
        }
        return createExportSnapshot(comparisonResult.value, selectedExperiments.value, lastUpdated.value)
      },
      generate: async snapshot => {
        if (!target) return { blob: new Blob([buildComparisonCsv(snapshot)], { type: 'text/csv;charset=utf-8' }), name: 'comparison', extension: 'csv' as const }
        await nextTick()
        let spec: ChartExportSpec | null = null
        if (target.kind === 'custom') {
          for (const component of customCharts.value) {
            spec = component.getExportSpec(target)
            if (spec) break
          }
        } else spec = builtinCharts.value?.getExportSpec(target) ?? null
        if (!spec) throw new Error('该图表已不存在或没有有效指标，本次未导出图片。')
        const blob = await createChartPng(spec, snapshot.fetchedAt, snapshot.exportedAt)
        return { blob, name: spec.filename, extension: 'png' as const }
      },
      deliver: (artifact, snapshot) => downloadBlob(artifact.blob, exportFilename(artifact.name, snapshot.exportedAt, artifact.extension)),
    })
    if (saved && !disposed) ElMessage.success('已生成导出文件，请查看浏览器下载记录。')
  } catch (error: unknown) {
    if (!disposed) {
      exportError.value = error instanceof Error ? error.message : '导出失败，请重试。'
      ElMessage.error(exportError.value)
    }
  } finally {
    exporting.value = false
    autoRefresh.settle()
  }
}

function receiveChange(change: ComparisonChange): void {
  if (!affectsComparison(change, selectedExperiments.value)) return
  if (change.kind === 'experiment' && change.deleted) {
    clearComparison()
    experiments.value = experiments.value.filter(item => item.id !== change.id)
    compareError.value = `已选实验 ID ${change.id} 已删除，请移除该实验后重新比较。`
    return
  }
  if (comparisonStarted.value) dataStale.value = true
  autoRefresh.request()
}

function checkLatest(): void {
  if (document.visibilityState !== 'visible') return
  autoRefresh.request()
}

function projectName(experiment: ComparisonExperiment): string {
  const metadata = selectedById.value.get(experiment.id)
  return metadata?.project_id === experiment.project_id ? metadata.project_name : `Project #${experiment.project_id}`
}

function batchName(experiment: ComparisonExperiment): string {
  const metadata = selectedById.value.get(experiment.id)
  return metadata?.batch_id === experiment.batch_id ? metadata.batch_name : `Batch #${experiment.batch_id}`
}

function metricValue(experiment: ComparisonExperiment, metric: MetricName): number | string {
  const value = experiment.result?.[metric]
  return value === null || value === undefined ? '-' : value
}

function isBest(experimentId: number, metric: MetricName): boolean {
  return comparisonResult.value?.best_by_metric[metric].experiment_ids.includes(experimentId) ?? false
}

function metricHeading(metric: MetricName, label: string): string {
  return `${label} ${comparisonResult.value?.best_by_metric[metric].direction === 'min' ? '↓' : '↑'}`
}

function customMetricHeading(metric: CustomMetricComparison): string {
  return `${metric.project_name} / ${metricLabel(metric.definition)} ${metric.definition.direction === 'min' ? '↓' : '↑'}`
}

onMounted(() => {
  void loadProjects()
  unsubscribeChanges = subscribeComparisonChanges(receiveChange)
  window.addEventListener('focus', checkLatest)
  document.addEventListener('visibilitychange', checkLatest)
})
onBeforeUnmount(() => {
  disposed = true; exportVersion += 1; restoreRequest += 1
  projectRequest += 1; batchRequest += 1; experimentRequest += 1; compareRequest += 1
  compareAbort?.abort()
  autoRefresh.dispose()
  unsubscribeChanges?.()
  window.removeEventListener('focus', checkLatest)
  document.removeEventListener('visibilitychange', checkLatest)
})
</script>

<template>
  <section class="page-heading"><h1>实验比较</h1><p>比较系统指标及项目自定义指标。↑ 越大越好，↓ 越小越好；自定义指标按所属项目分别比较。</p></section>
  <el-dialog v-model="candidateOpen" title="添加实验" width="min(1000px, 94vw)">
  <el-card shadow="never" class="comparison-card">
    <template #header><div class="card-header"><h2>候选实验</h2>
      <div class="card-actions">
        <el-button :loading="projectsLoading" @click="loadProjects">刷新项目</el-button>
        <el-button :loading="batchesLoading" :disabled="!projectId" @click="loadBatches">刷新批次</el-button>
        <el-button :loading="experimentsLoading" :disabled="!batchId" @click="loadExperiments">刷新候选实验</el-button>
      </div>
    </div></template>
    <el-alert v-if="projectsError" :title="projectsError" type="error" :closable="false" show-icon />
    <el-empty v-else-if="!projectsLoading && projects.length === 0" description="暂无实验项目，请先创建项目。">
      <el-button @click="router.push('/projects')">前往项目管理</el-button>
    </el-empty>
    <template v-else>
      <div class="context-selectors">
        <div><label for="compare-project">实验项目</label>
          <el-select id="compare-project" v-model="projectId" aria-label="实验项目" placeholder="请选择实验项目"
                     :loading="projectsLoading" :disabled="projectsLoading" @change="selectProject">
            <el-option v-for="project in projects" :key="project.id" :label="project.name" :value="project.id" />
          </el-select>
        </div>
        <div><label for="compare-batch">实验批次</label>
          <el-select id="compare-batch" v-model="batchId" aria-label="实验批次" placeholder="请选择实验批次"
                     :loading="batchesLoading" :disabled="!projectId || batchesLoading" @change="selectBatch">
            <el-option v-for="batch in batches" :key="batch.id" :label="batch.name" :value="batch.id" />
          </el-select>
        </div>
      </div>
      <el-alert v-if="batchesError" :title="batchesError" type="error" :closable="false" show-icon />
      <el-empty v-else-if="projectId && !batchesLoading && batches.length === 0" description="当前项目暂无实验批次。">
        <el-button @click="router.push('/projects')">前往项目管理</el-button>
      </el-empty>
      <el-empty v-else-if="!batchId" description="请选择项目和批次加载候选实验" />
      <el-alert v-else-if="experimentsError" :title="experimentsError" type="error" :closable="false" show-icon />
      <el-empty v-else-if="!experimentsLoading && experiments.length === 0" description="当前批次暂无实验记录。">
        <el-button @click="router.push({ path: '/experiments', query: { projectId, batchId } })">前往实验管理</el-button>
      </el-empty>
      <el-table v-else v-loading="experimentsLoading" :data="experiments" row-key="id" aria-label="候选实验列表">
        <el-table-column prop="experiment_no" label="实验编号" min-width="140" show-overflow-tooltip />
        <el-table-column prop="model_name" label="模型名称" min-width="140" show-overflow-tooltip />
        <el-table-column label="参数" min-width="240" show-overflow-tooltip><template #default="{ row }">{{ JSON.stringify(row.parameters) }}</template></el-table-column>
        <el-table-column label="备注" min-width="160" show-overflow-tooltip><template #default="{ row }">{{ row.notes ?? '-' }}</template></el-table-column>
        <el-table-column label="操作" width="120"><template #default="{ row }">
          <el-button link type="primary" :disabled="comparisonBusy || experimentsLoading || selectedById.has(row.id)" @click="addExperiment(row)">{{ selectedById.has(row.id) ? '已加入' : '加入比较' }}</el-button>
        </template></el-table-column>
      </el-table>
    </template>
  </el-card>

  <template #footer><el-button @click="candidateOpen = false">完成选择</el-button></template>
  </el-dialog>

  <el-card shadow="never" class="comparison-card">
    <template #header><div class="card-header"><h2>已选实验（{{ selectedExperiments.length }}）</h2>
      <div class="card-actions">
        <el-button :disabled="comparisonBusy" @click="candidateOpen = true">添加实验</el-button>
        <el-button :disabled="comparisonBusy || selectedExperiments.length === 0" @click="clearSelection">清空选择</el-button>
        <el-button type="primary" :loading="compareLoading" :disabled="comparisonBusy || selectedExperiments.length < 2" @click="startComparison">{{ comparisonResult ? '重新比较' : '开始比较' }}</el-button>
      </div>
    </div></template>
    <el-empty v-if="selectedExperiments.length === 0" description="点击“添加实验”，或从项目工作区勾选实验后进入比较。" />
    <template v-else>
      <p v-if="selectedExperiments.length === 1" class="hint">还需至少选择 1 个实验。</p>
      <div class="baseline-selector">
        <label for="compare-baseline">基准实验（可选）</label>
        <el-select id="compare-baseline" v-model="baselineId" aria-label="基准实验" clearable :value-on-clear="null" :disabled="comparisonBusy" placeholder="不选择基准，只比较原始指标">
          <el-option v-for="experiment in selectedExperiments" :key="experiment.id" :value="experiment.id" :label="`${experiment.experiment_no} / ${experiment.project_name}`" />
        </el-select>
        <p class="hint">选择后点击开始比较。差值为当前实验减基准，按指标方向判断改善或退步；缺失值不补 0。</p>
      </div>
      <div class="selected-list" aria-label="已选实验列表" v-loading="restoring">
        <el-tag v-for="experiment in selectedExperiments" :key="experiment.id" size="large"
          :type="experiment.missing ? 'danger' : experiment.id === baselineId ? 'warning' : 'info'"
          :closable="!comparisonBusy" :title="`${experiment.project_name} / ${experiment.batch_name} / ${experiment.model_name}`"
          @close="removeExperiment(experiment.id)">
          {{ experiment.experiment_no }}{{ experiment.id === baselineId ? ' · 基准' : '' }}
        </el-tag>
      </div>
    </template>
  </el-card>

  <el-card shadow="never" class="comparison-card">
    <template #header><div class="card-header">
      <div class="result-heading"><h2>比较结果</h2>
        <el-popover v-model:visible="comparisonHelpOpen" placement="bottom-start" :width="320" trigger="click" title="比较与导出说明">
          <template #reference><el-button class="help-button" circle size="small" aria-label="查看比较与导出说明" @keydown.esc.stop="comparisonHelpOpen = false">?</el-button></template>
          <div class="comparison-help">
            <p>开始比较后，相关数据更新或切回本页时会自动刷新，也可点击“重新比较”。</p>
            <p>最近获取：{{ lastUpdatedLabel }}</p>
            <p>导出前会刷新数据。CSV 包含原始指标、最佳结果及已选基准的差值；图表可分别导出 PNG。</p>
          </div>
        </el-popover>
      </div>
      <el-button :loading="exporting" :disabled="comparisonBusy || !comparisonResult" @click="exportComparison()">导出比较表 CSV</el-button>
    </div></template>
    <p v-if="syncStatus" class="hint" role="status" aria-label="比较同步状态" aria-live="polite">{{ syncStatus }}</p>
    <p v-if="exporting" class="hint" role="status" aria-live="polite">正在刷新并生成导出文件，请稍候…</p>
    <el-alert v-if="exportError" :title="exportError" type="error" :closable="false" show-icon />
    <div v-loading="compareLoading" class="result-content">
      <el-alert v-if="compareError" :title="compareError" type="error" :closable="false" show-icon />
      <el-empty v-if="!comparisonResult && !compareError" description="选择至少两个实验后开始比较。" />
      <template v-if="comparisonResult">
        <p v-if="baselineExperiment" class="hint baseline-summary">相对基准：{{ baselineExperiment.experiment_no }}。表格保留原始指标，并显示绝对差值和状态；图表仍展示原始数值。</p>
        <el-alert v-if="baselineExperiment && isCrossProject" title="系统指标的跨项目差值仅作数值对照，请确认评测条件一致；自定义指标只在所属项目内计算差值。" type="info" :closable="false" show-icon />
        <ul class="best-summary" aria-label="最佳指标摘要">
          <li v-for="metric in metrics" :key="metric.key">
            <span>{{ metric.label }}：</span>
            <span v-if="comparisonResult.best_by_metric[metric.key].value === null">暂无可比较数据</span>
            <span v-else>最佳 {{ comparisonResult.best_by_metric[metric.key].value }}<span v-if="comparisonResult.best_by_metric[metric.key].experiment_ids.length > 1">（{{ comparisonResult.best_by_metric[metric.key].experiment_ids.length }} 个实验并列）</span></span>
          </li>
        </ul>
        <template v-if="comparisonResult.custom_metrics?.length">
          <h3>项目自定义指标</h3>
          <ul class="best-summary" aria-label="自定义指标最佳摘要">
            <li v-for="metric in comparisonResult.custom_metrics" :key="`${metric.definition.project_id}:${metric.definition.key}`">
              {{ customMetricHeading(metric) }}：
              <span v-if="metric.best.value === null">暂无可比较数据</span>
              <span v-else>最佳 {{ metric.best.value }}<span v-if="metric.best.experiment_ids.length > 1">（{{ metric.best.experiment_ids.length }} 个实验并列）</span></span>
            </li>
          </ul>
        </template>
        <el-table :data="comparisonResult.experiments" row-key="id" aria-label="实验比较结果列表">
          <el-table-column label="实验编号" min-width="140" show-overflow-tooltip><template #default="{ row }"><div class="metric-cell">{{ row.experiment_no }}<el-tag v-if="row.id === comparisonResult.baseline_comparison?.baseline_experiment_id" type="warning" size="small">基准</el-tag></div></template></el-table-column>
          <el-table-column prop="model_name" label="模型名称" min-width="120" show-overflow-tooltip />
          <el-table-column label="项目" min-width="120" show-overflow-tooltip><template #default="{ row }">{{ projectName(row) }}</template></el-table-column>
          <el-table-column label="批次" min-width="110" show-overflow-tooltip><template #default="{ row }">{{ batchName(row) }}</template></el-table-column>
          <el-table-column v-for="metric in comparisonResult.custom_metrics ?? []" :key="`${metric.definition.project_id}:${metric.definition.key}`" :label="customMetricHeading(metric)" :min-width="comparisonResult.baseline_comparison ? 220 : 180">
            <template #default="{ row }"><div class="metric-cell"><span>{{ metric.values[row.id] ?? '-' }}</span><el-tag v-if="metric.best.experiment_ids.includes(row.id)" type="success" size="small">最佳</el-tag></div><MetricDeltaDisplay v-if="comparisonResult.baseline_comparison" :value="deltaValue(row.id, metric.definition.key, metric.definition.project_id)" :unit="metric.definition.unit" /></template>
          </el-table-column>
          <el-table-column v-for="metric in metrics" :key="metric.key" :label="metricHeading(metric.key, metric.label)" :min-width="comparisonResult.baseline_comparison ? 180 : 106">
            <template #default="{ row }"><div class="metric-cell"><span>{{ metricValue(row, metric.key) }}</span><el-tag v-if="isBest(row.id, metric.key)" type="success" size="small">最佳</el-tag></div><MetricDeltaDisplay v-if="comparisonResult.baseline_comparison" :value="deltaValue(row.id, metric.key)" /></template>
          </el-table-column>
          <el-table-column label="结果状态" width="110"><template #default="{ row }"><el-tag :type="row.result === null ? 'info' : 'success'" size="small">{{ row.result === null ? '未录入结果' : '已录入结果' }}</el-tag></template></el-table-column>
        </el-table>
        <ComparisonCharts v-if="showBuiltinCharts" ref="builtinCharts" :result="comparisonResult" :export-disabled="comparisonBusy" @export-chart="exportComparison" />
        <CustomMetricChart v-for="metric in comparisonResult.custom_metrics ?? []" :key="`${metric.definition.project_id}:${metric.definition.key}`" ref="customCharts" :metric="metric" :experiments="comparisonResult.experiments" :export-disabled="comparisonBusy" @export-chart="exportComparison" />
      </template>
    </div>
  </el-card>
  <AiExperimentSummary :experiments="selectedExperiments" :baseline-id="baselineId" :comparison-updated-at="lastUpdated" />
</template>

<style scoped>
.selected-list { display: flex; flex-wrap: wrap; gap: 8px; }
.selected-list .el-tag { max-width: 100%; height: auto; min-height: 32px; white-space: normal; overflow-wrap: anywhere; }
.hint { color: #6b7280; line-height: 1.7; }
.result-heading { display: flex; align-items: center; gap: 8px; }
.help-button { color: #6b7280; font-weight: 600; }
.comparison-help { line-height: 1.7; overflow-wrap: anywhere; }
.comparison-help p { margin: 0 0 10px; }
.comparison-help p:last-child { margin-bottom: 0; }
.result-content { min-height: 120px; }
.metric-cell { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
.baseline-selector { margin-bottom: 16px; }
.baseline-selector label { display: block; margin-bottom: 8px; font-weight: 600; }
.baseline-selector .el-select { width: min(100%, 520px); }
.baseline-summary { margin-top: 0; }
.best-summary { display: flex; flex-wrap: wrap; gap: 12px 24px; list-style: none; margin: 0 0 20px; padding: 0; color: #4b5563; font-size: 14px; line-height: 1.8; }
</style>
