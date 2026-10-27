<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { ComparisonExperiment, ExperimentCompareResponse } from '../api/compare'
import type { ComparisonCell } from '../utils/comparison-table'
import { comparisonExperimentPage, comparisonMetricRows, experimentColumnCapacity, filterComparisonMetrics } from '../utils/comparison-table'
import { formatSignedDelta } from '../utils/metric-delta'
import { deltaReasonLabels, deltaStatusLabels } from '../utils/comparison-export'

const props = defineProps<{ result: ExperimentCompareResponse; metadata: { id: number; project_id: number; project_name: string; batch_id: number; batch_name: string }[]; active: boolean }>()
const root = ref<HTMLElement>()
const width = ref(900)
const page = ref(1)
const search = ref('')
const hideEmpty = ref(true)
const excludedIds = ref<string[]>([])
const metricPickerOpen = ref(false)
const rows = computed(() => comparisonMetricRows(props.result))
const filteredRows = computed(() => filterComparisonMetrics(rows.value, excludedIds.value, search.value, hideEmpty.value))
const emptyCount = computed(() => rows.value.filter(row => !row.hasData).length)
const crossProject = computed(() => new Set(props.result.experiments.map(item => item.project_id)).size > 1)
const baselineId = computed(() => props.result.baseline_comparison?.baseline_experiment_id)
const capacity = computed(() => experimentColumnCapacity(width.value, baselineId.value !== undefined))
const group = computed(() => comparisonExperimentPage(props.result.experiments, baselineId.value, capacity.value, page.value))
const names = computed(() => new Map(props.metadata.map(item => [item.id, item])))
const metricWidth = computed(() => Math.max(96, Math.min(180, width.value * .25)))
const statusLabels = { missing: '缺失指标', 'no-result': '未录入结果', 'not-applicable': '不适用（其他项目）', value: '' }
let observer: ResizeObserver | undefined

function setIncluded(id: string, included: boolean): void {
  excludedIds.value = included ? excludedIds.value.filter(item => item !== id) : [...new Set([...excludedIds.value, id])]
}
function restoreAll(): void { excludedIds.value = []; hideEmpty.value = false; search.value = '' }
function projectName(experiment: ComparisonExperiment): string {
  const name = names.value.get(experiment.id)
  return name?.project_id === experiment.project_id ? name.project_name : `Project #${experiment.project_id}`
}
function batchName(experiment: ComparisonExperiment): string {
  const name = names.value.get(experiment.id)
  return name?.batch_id === experiment.batch_id ? name.batch_name : `Batch #${experiment.batch_id}`
}
function deltaText(cell: ComparisonCell): string {
  if (!cell.delta || cell.delta.delta === null) return ''
  return `Δ ${formatSignedDelta(cell.delta.delta)} · ${deltaStatusLabels[cell.delta.status]}`
}
function deltaHint(cell: ComparisonCell): string {
  if (cell.delta?.reason) return deltaReasonLabels[cell.delta.reason]
  return cell.delta?.delta !== null && cell.delta?.delta !== undefined ? `差值：${cell.delta.delta}` : '未提供差值'
}

watch(() => group.value.page, value => { page.value = value })
watch(() => props.result.experiments.map(item => item.id).join(','), () => { page.value = 1 })
watch(() => rows.value.map(row => row.id).join('|'), () => {
  const existing = new Set(rows.value.map(row => row.id))
  excludedIds.value = excludedIds.value.filter(id => existing.has(id))
})
watch(() => props.active, active => { if (!active) metricPickerOpen.value = false })
onMounted(() => {
  observer = new ResizeObserver(entries => {
    const nextWidth = entries[0]?.contentRect.width
    if (nextWidth && nextWidth > 0) width.value = nextWidth
  })
  if (root.value) observer.observe(root.value)
})
onBeforeUnmount(() => observer?.disconnect())
</script>

<template>
  <div ref="root" class="metric-comparison">
    <div class="metric-tools">
      <el-input v-model="search" class="metric-search" aria-label="搜索比较指标" placeholder="搜索指标名称、键或单位" clearable />
      <el-popover v-model:visible="metricPickerOpen" placement="bottom-end" :width="300" trigger="click">
        <template #reference><el-button>选择指标（{{ rows.length - excludedIds.length }}/{{ rows.length }}）</el-button></template>
        <div class="picker-heading"><strong>显示的指标</strong><el-button link type="primary" @click="excludedIds = []">全选</el-button><el-button link @click="excludedIds = rows.map(row => row.id)">清空</el-button></div>
        <div class="metric-options"><el-checkbox v-for="row in rows" :key="row.id" class="metric-option" :model-value="!excludedIds.includes(row.id)" :aria-label="`显示指标 ${row.projectId === null ? '' : `${row.projectName} / `}${row.name}${row.unit ? `（${row.unit}）` : ''}`" @change="setIncluded(row.id, Boolean($event))"><span>{{ row.name }}{{ row.unit ? `（${row.unit}）` : '' }}<small>{{ row.projectId === null ? '系统指标' : row.projectName }} · {{ row.key }}</small></span></el-checkbox></div>
      </el-popover>
      <el-button @click="restoreAll">恢复全部指标</el-button>
    </div>
    <div class="table-context">
      <span>显示 {{ filteredRows.length }} / {{ rows.length }} 项指标</span>
      <button v-if="emptyCount" type="button" class="empty-toggle" :aria-pressed="!hideEmpty" @click="hideEmpty = !hideEmpty">{{ hideEmpty ? `展开 ${emptyCount} 项暂无数据指标` : '收起暂无数据指标' }}</button>
      <span class="best-legend"><span aria-hidden="true">★</span> 最佳值按全部 {{ result.experiments.length }} 个实验计算</span>
    </div>
    <div class="experiment-pager" aria-label="实验列分组">
      <span class="group-status" role="status" aria-live="polite">{{ group.baselineId ? '基准固定 · ' : '' }}{{ group.baselineId ? '其他实验' : '实验' }} {{ group.first }}–{{ group.last }} / {{ group.otherCount }}<span v-if="group.pageCount > 1"> · 第 {{ group.page }} / {{ group.pageCount }} 组</span></span>
      <div v-if="group.pageCount > 1" class="pager-actions"><el-button size="small" :disabled="group.page === 1" aria-label="上一组实验" @click="page = group.page - 1">上一组</el-button><el-button size="small" :disabled="group.page === group.pageCount" aria-label="下一组实验" @click="page = group.page + 1">下一组</el-button></div>
    </div>
    <div class="document-table-frame">
      <table class="document-table" aria-label="实验指标对照表">
        <caption class="sr-only">指标按行、实验按列；↑ 越大越好，↓ 越小越好；星号表示全部已选实验中的最佳值。</caption>
        <colgroup><col :style="{ width: `${metricWidth}px` }" /><col v-for="experiment in group.experiments" :key="experiment.id" /></colgroup>
        <thead><tr><th scope="col" class="metric-heading">评价指标<span>方向 / 单位</span></th><th v-for="experiment in group.experiments" :key="experiment.id" scope="col" :data-experiment-id="experiment.id" :class="{ 'baseline-header': experiment.id === baselineId }"><span v-if="experiment.id === baselineId" class="baseline-label">基准</span><strong>{{ experiment.experiment_no }}</strong><span class="model-name">{{ experiment.model_name }}</span><span v-if="experiment.result === null" class="missing-result">未录入结果</span></th></tr></thead>
        <tbody>
          <tr v-for="row in filteredRows" :key="row.id" :data-metric-id="row.id">
            <th scope="row"><div class="row-name">{{ row.name }} <span class="direction" :title="row.direction === 'max' ? '越大越好' : '越小越好'" :aria-label="row.direction === 'max' ? '越大越好' : '越小越好'">{{ row.direction === 'max' ? '↑' : '↓' }}</span></div><span v-if="row.unit" class="row-unit">{{ row.unit }}</span><span v-if="row.projectId !== null" class="row-project">{{ crossProject ? row.projectName : '项目指标' }}</span></th>
            <td v-for="experiment in group.experiments" :key="experiment.id" :data-experiment-id="experiment.id" :data-status="row.cells[experiment.id]!.status" :class="{ 'best-cell': row.cells[experiment.id]!.best, 'baseline-cell': experiment.id === baselineId }">
              <div v-if="row.cells[experiment.id]!.value !== null" class="value-line"><span class="metric-value" :title="String(row.cells[experiment.id]!.value)">{{ row.cells[experiment.id]!.value }}</span><span v-if="row.cells[experiment.id]!.best" class="best-mark" aria-label="最佳" title="全部已选实验中的最佳值">★</span></div>
              <span v-else class="missing-value" :title="statusLabels[row.cells[experiment.id]!.status]">{{ row.cells[experiment.id]!.status === 'not-applicable' ? '不适用' : '—' }}<span class="sr-only">{{ statusLabels[row.cells[experiment.id]!.status] }}</span></span>
              <template v-if="baselineId && experiment.id !== baselineId">
                <span v-if="deltaText(row.cells[experiment.id]!)" class="cell-delta" :data-status="row.cells[experiment.id]!.delta?.status" :title="deltaHint(row.cells[experiment.id]!)">{{ deltaText(row.cells[experiment.id]!) }}</span>
                <span v-else class="cell-delta unavailable" :title="deltaHint(row.cells[experiment.id]!)">无法比较<span class="sr-only">：{{ deltaHint(row.cells[experiment.id]!) }}</span></span>
              </template>
            </td>
          </tr>
          <tr v-if="!filteredRows.length"><td :colspan="group.experiments.length + 1" class="empty-metrics">{{ search.trim() ? '没有匹配的指标，可修改搜索或恢复全部指标。' : '当前没有显示的指标，可选择指标或恢复全部。' }}</td></tr>
        </tbody>
      </table>
    </div>
    <details class="experiment-info"><summary>实验信息（{{ result.experiments.length }}）</summary><div class="info-grid"><article v-for="experiment in result.experiments" :key="experiment.id"><strong>{{ experiment.experiment_no }}</strong><dl><dt>模型</dt><dd>{{ experiment.model_name }}</dd><dt>项目</dt><dd>{{ projectName(experiment) }}</dd><dt>批次</dt><dd>{{ batchName(experiment) }}</dd><dt>结果</dt><dd>{{ experiment.result === null ? '未录入结果' : '已录入结果' }}</dd></dl></article></div></details>
  </div>
</template>

<style scoped>
.metric-comparison { min-width: 0; color: #24354a; }
.metric-tools { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 12px; }
.metric-tools .el-button { margin: 0; }
.metric-search { width: min(100%, 300px); }
.picker-heading { display: flex; align-items: center; gap: 10px; padding-bottom: 10px; border-bottom: 1px solid #e5eaf0; }
.picker-heading strong { margin-right: auto; }
.metric-options { max-height: 340px; overflow-y: auto; padding-top: 8px; }
.metric-option { display: flex; align-items: center; gap: 9px; padding: 7px 0; cursor: pointer; font-size: 13px; overflow-wrap: anywhere; }
.metric-option { height: auto; margin: 0; width: 100%; white-space: normal; }
.metric-option :deep(.el-checkbox__label) { min-width: 0; white-space: normal; overflow-wrap: anywhere; }
.metric-option small { display: block; color: #64748b; font-size: 11px; line-height: 1.6; }
.table-context { display: flex; align-items: center; gap: 8px 16px; flex-wrap: wrap; color: #64748b; font-size: 12px; line-height: 1.8; margin-bottom: 18px; }
.empty-toggle { padding: 0; background: none; border: none; color: #326aa0; font: inherit; cursor: pointer; text-decoration: underline; text-underline-offset: 3px; }
.best-legend { margin-left: auto; }.best-legend > span { color: #26825e; margin-right: 4px; }
.experiment-pager { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; min-height: 32px; margin: 0 0 12px; }
.group-status { color: #526479; font-size: 12px; }.pager-actions { display: flex; gap: 8px; }.pager-actions .el-button { margin: 0; }
.document-table-frame { border: 1px solid #ced8e3; border-radius: 8px; }
.document-table { width: 100%; table-layout: fixed; border-spacing: 0; border-collapse: separate; font-size: 14px; }
.document-table th, .document-table td { padding: 18px 16px; border-right: 1px solid #dce3eb; border-bottom: 1px solid #dce3eb; overflow-wrap: anywhere; vertical-align: middle; }
.document-table tr > :last-child { border-right: 0; }.document-table tbody tr:last-child > * { border-bottom: 0; }
.document-table thead th { background: #f0f4f8; text-align: center; font-weight: 600; position: sticky; top: 0; z-index: 1; box-shadow: 0 1px 0 #dce3eb; }
.document-table thead th:first-child { border-top-left-radius: 8px; }.document-table thead th:last-child { border-top-right-radius: 8px; }
.document-table thead .metric-heading { text-align: left; }.metric-heading > span { display: block; font-size: 11px; font-weight: 400; color: #64748b; margin-top: 8px; }
.document-table thead strong { display: block; line-height: 1.6; }.model-name { display: block; font-size: 12px; color: #64748b; font-weight: 400; line-height: 1.6; margin-top: 5px; }
.document-table tbody th { background: #f9fbfd; text-align: left; font-weight: 500; }.row-name { line-height: 1.6; }.direction { font-size: 13px; color: #648195; white-space: nowrap; }.row-unit, .row-project { display: block; color: #64748b; font-size: 11px; line-height: 1.6; margin-top: 4px; }
.document-table td { text-align: center; background: #fff; }.document-table .best-cell { background: #edf8f1; }.metric-value { font-variant-numeric: tabular-nums; line-height: 1.6; }.best-cell .metric-value { font-weight: 700; color: #206548; }
.value-line { display: flex; justify-content: center; align-items: baseline; gap: 6px; }.best-mark { font-size: 11px; color: #26825e; flex-shrink: 0; }
.document-table thead .baseline-header { background: #eef2fc; }.document-table .baseline-cell { border-right: 2px solid #bccce1; }.baseline-label { display: inline-block; background: #dce5f8; color: #44608d; padding: 2px 7px; border-radius: 4px; font-size: 10px; margin-bottom: 7px; }.missing-result { display: block; color: #8a6c3d; font-size: 11px; font-weight: 400; margin-top: 6px; }
.missing-value { color: #8b98a8; font-size: 13px; }.cell-delta { display: block; margin-top: 7px; color: #64748b; font-size: 11px; line-height: 1.7; font-variant-numeric: tabular-nums; }.cell-delta[data-status='improved'] { color: #2f805b; }.cell-delta[data-status='regressed'] { color: #b04f4f; }.cell-delta.unavailable { color: #8b98a8; }
.document-table .empty-metrics { padding: 38px 16px; color: #64748b; font-size: 13px; }
.experiment-info { margin-top: 20px; color: #526479; font-size: 12px; }.experiment-info summary { cursor: pointer; width: fit-content; padding: 6px 0; }.info-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 240px), 1fr)); gap: 12px; margin-top: 12px; }.info-grid article { border: 1px solid #e0e6ef; border-radius: 7px; background: #f9fbfd; padding: 16px; overflow-wrap: anywhere; }.info-grid strong { color: #334155; font-size: 13px; }.info-grid dl { display: grid; grid-template-columns: 32px minmax(0, 1fr); gap: 8px 12px; line-height: 1.7; margin-bottom: 0; }.info-grid dt { color: #7c8b9c; }.info-grid dd { margin: 0; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
button:focus-visible, summary:focus-visible { outline: 2px solid #326aa0; outline-offset: 4px; }
@media (max-width: 600px) { .metric-search { width: 100%; }.best-legend { margin-left: 0; }.document-table th, .document-table td { padding: 14px 8px; font-size: 12px; }.model-name { font-size: 10px; }.value-line { gap: 3px; }.cell-delta { font-size: 10px; }.row-unit, .row-project { font-size: 10px; } }
</style>
