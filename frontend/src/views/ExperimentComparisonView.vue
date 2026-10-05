<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getProjects } from '../api/projects'
import type { Project } from '../api/projects'
import { getProjectBatches } from '../api/batches'
import type { ExperimentBatch } from '../api/batches'
import { getBatchExperiments } from '../api/experiments'
import type { Experiment } from '../api/experiments'
import { compareExperiments } from '../api/compare'
import type { ComparisonExperiment, ExperimentCompareResponse, MetricName } from '../api/compare'
import { getApiErrorMessage } from '../api/errors'
import ComparisonCharts from '../components/ComparisonCharts.vue'

interface SelectedExperiment {
  id: number
  experiment_no: string
  model_name: string
  project_id: number
  project_name: string
  batch_id: number
  batch_name: string
}

const router = useRouter()
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
const projectsLoading = ref(false)
const batchesLoading = ref(false)
const experimentsLoading = ref(false)
const compareLoading = ref(false)
const projectsError = ref('')
const batchesError = ref('')
const experimentsError = ref('')
const compareError = ref('')
let projectRequest = 0
let batchRequest = 0
let experimentRequest = 0
let compareRequest = 0
const metrics: { key: MetricName; label: string }[] = [
  { key: 'accuracy', label: 'Accuracy' }, { key: 'precision', label: 'Precision' },
  { key: 'recall', label: 'Recall' }, { key: 'f1', label: 'F1' }, { key: 'loss', label: 'Loss' },
]

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
  compareRequest += 1
  comparisonResult.value = null
  compareError.value = ''
}

function addExperiment(experiment: Experiment): void {
  if (compareLoading.value || selectedById.value.has(experiment.id) || !selectedProject.value || !selectedBatch.value) return
  if (experiment.batch_id !== selectedBatch.value.id) return
  selectedExperiments.value.push({
    id: experiment.id, experiment_no: experiment.experiment_no, model_name: experiment.model_name,
    project_id: selectedProject.value.id, project_name: selectedProject.value.name,
    batch_id: selectedBatch.value.id, batch_name: selectedBatch.value.name,
  })
  clearComparison()
}

function removeExperiment(id: number): void {
  if (compareLoading.value) return
  selectedExperiments.value = selectedExperiments.value.filter(experiment => experiment.id !== id)
  clearComparison()
}

function clearSelection(): void {
  if (compareLoading.value) return
  selectedExperiments.value = []
  clearComparison()
}

async function startComparison(): Promise<void> {
  if (compareLoading.value || selectedExperiments.value.length < 2) return
  const request = ++compareRequest
  const ids = selectedExperiments.value.map(experiment => experiment.id)
  compareLoading.value = true
  compareError.value = ''
  try {
    const response = await compareExperiments(ids)
    if (request === compareRequest) comparisonResult.value = response
  } catch (error: unknown) {
    if (request === compareRequest) {
      comparisonResult.value = null
      compareError.value = getApiErrorMessage(error, '实验比较失败，请重试。')
      ElMessage.error(compareError.value)
    }
  } finally { if (request === compareRequest) compareLoading.value = false }
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

onMounted(loadProjects)
onBeforeUnmount(() => { projectRequest += 1; batchRequest += 1; experimentRequest += 1; compareRequest += 1 })
</script>

<template>
  <section class="page-heading"><h1>实验比较</h1><p>从不同项目与批次加入实验，比较五项当前结果指标。↑ 越大越好，↓ 越小越好。</p></section>
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
          <el-button link type="primary" :disabled="compareLoading || experimentsLoading || selectedById.has(row.id)" @click="addExperiment(row)">{{ selectedById.has(row.id) ? '已加入' : '加入比较' }}</el-button>
        </template></el-table-column>
      </el-table>
    </template>
  </el-card>

  <el-card shadow="never" class="comparison-card">
    <template #header><div class="card-header"><h2>已选实验（{{ selectedExperiments.length }}）</h2>
      <div class="card-actions">
        <el-button :disabled="compareLoading || selectedExperiments.length === 0" @click="clearSelection">清空选择</el-button>
        <el-button type="primary" :loading="compareLoading" :disabled="compareLoading || selectedExperiments.length < 2" @click="startComparison">{{ comparisonResult ? '重新比较' : '开始比较' }}</el-button>
      </div>
    </div></template>
    <el-empty v-if="selectedExperiments.length === 0" description="请从上方候选实验中加入需要比较的实验。" />
    <template v-else>
      <p v-if="selectedExperiments.length === 1" class="hint">还需至少选择 1 个实验。</p>
      <el-table :data="selectedExperiments" row-key="id" aria-label="已选实验列表">
        <el-table-column prop="experiment_no" label="实验编号" min-width="140" show-overflow-tooltip />
        <el-table-column prop="model_name" label="模型名称" min-width="140" show-overflow-tooltip />
        <el-table-column prop="project_name" label="项目" min-width="180" show-overflow-tooltip />
        <el-table-column prop="batch_name" label="批次" min-width="180" show-overflow-tooltip />
        <el-table-column label="操作" width="90"><template #default="{ row }"><el-button link type="danger" :disabled="compareLoading" @click="removeExperiment(row.id)">移除</el-button></template></el-table-column>
      </el-table>
    </template>
  </el-card>

  <el-card shadow="never" class="comparison-card">
    <template #header><h2>比较结果</h2></template>
    <div v-loading="compareLoading" class="result-content">
      <el-alert v-if="compareError" :title="compareError" type="error" :closable="false" show-icon />
      <el-empty v-else-if="!comparisonResult" description="选择至少两个实验后开始比较。" />
      <template v-else>
        <ul class="best-summary" aria-label="最佳指标摘要">
          <li v-for="metric in metrics" :key="metric.key">
            <span>{{ metric.label }}：</span>
            <span v-if="comparisonResult.best_by_metric[metric.key].value === null">暂无可比较数据</span>
            <span v-else>最佳 {{ comparisonResult.best_by_metric[metric.key].value }}<span v-if="comparisonResult.best_by_metric[metric.key].experiment_ids.length > 1">（{{ comparisonResult.best_by_metric[metric.key].experiment_ids.length }} 个实验并列）</span></span>
          </li>
        </ul>
        <ComparisonCharts :result="comparisonResult" />
        <el-table :data="comparisonResult.experiments" row-key="id" aria-label="实验比较结果列表">
          <el-table-column prop="experiment_no" label="实验编号" min-width="120" show-overflow-tooltip />
          <el-table-column prop="model_name" label="模型名称" min-width="120" show-overflow-tooltip />
          <el-table-column label="项目" min-width="120" show-overflow-tooltip><template #default="{ row }">{{ projectName(row) }}</template></el-table-column>
          <el-table-column label="批次" min-width="110" show-overflow-tooltip><template #default="{ row }">{{ batchName(row) }}</template></el-table-column>
          <el-table-column v-for="metric in metrics" :key="metric.key" :label="metricHeading(metric.key, metric.label)" min-width="106">
            <template #default="{ row }"><div class="metric-cell"><span>{{ metricValue(row, metric.key) }}</span><el-tag v-if="isBest(row.id, metric.key)" type="success" size="small">最佳</el-tag></div></template>
          </el-table-column>
          <el-table-column label="结果状态" width="110"><template #default="{ row }"><el-tag :type="row.result === null ? 'info' : 'success'" size="small">{{ row.result === null ? '未录入结果' : '已录入结果' }}</el-tag></template></el-table-column>
        </el-table>
      </template>
    </div>
  </el-card>
</template>

<style scoped>
.page-heading { margin-bottom: 28px; }
h1 { margin: 0 0 12px; font-size: 28px; }
.page-heading p, .hint { color: #6b7280; line-height: 1.7; }
.comparison-card { margin-bottom: 24px; }
.card-header { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 16px; }
h2 { margin: 0; font-size: 18px; }
.card-actions { display: flex; flex-wrap: wrap; gap: 8px; }
.card-actions .el-button { margin-left: 0; }
.context-selectors { display: flex; flex-wrap: wrap; gap: 20px; margin: 16px 0 24px; }
.context-selectors > div { flex: 1; min-width: 240px; }
.context-selectors label { display: block; margin-bottom: 8px; font-size: 14px; }
.context-selectors .el-select { width: 100%; }
.result-content { min-height: 120px; }
.metric-cell { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
.best-summary { display: flex; flex-wrap: wrap; gap: 12px 24px; list-style: none; margin: 0 0 20px; padding: 0; color: #4b5563; font-size: 14px; line-height: 1.8; }
</style>
