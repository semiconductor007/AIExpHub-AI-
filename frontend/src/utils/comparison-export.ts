import type { ComparisonExperiment, ExperimentCompareResponse, MetricDelta, MetricName } from '../api/compare'

export interface ExportExperimentMetadata {
  id: number
  project_id: number
  project_name: string
  batch_id: number
  batch_name: string
}

export interface ComparisonExportSnapshot {
  result: ExperimentCompareResponse
  metadata: ExportExperimentMetadata[]
  fetchedAt: string
  exportedAt: string
}

export const deltaStatusLabels = { improved: '改善', regressed: '退步', unchanged: '无变化', unavailable: '无法比较' }
export const deltaReasonLabels = {
  baseline_project_mismatch: '基准不属于该指标项目', experiment_project_mismatch: '实验不属于该指标项目',
  baseline_result_missing: '基准未录入结果', experiment_result_missing: '实验未录入结果',
  baseline_metric_missing: '基准缺少该指标', experiment_metric_missing: '实验缺少该指标', overflow: '差值超出有限数值范围',
}

export function createExportSnapshot(result: ExperimentCompareResponse, metadata: ExportExperimentMetadata[], fetchedAt: number, exportedAt = Date.now()): ComparisonExportSnapshot {
  // API data is JSON. Detach Vue proxies and later refreshes without rounding numeric values.
  return {
    result: JSON.parse(JSON.stringify(result)) as ExperimentCompareResponse,
    metadata: metadata.map(({ id, project_id, project_name, batch_id, batch_name }) => ({ id, project_id, project_name, batch_id, batch_name })),
    fetchedAt: new Date(fetchedAt).toISOString(), exportedAt: new Date(exportedAt).toISOString(),
  }
}

type CsvCell = string | number | null | undefined

export function csvCell(value: CsvCell): string {
  if (value === null || value === undefined) return '""'
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) throw new Error('导出数据含有非有限数值，请重新比较后重试。')
    return String(value)
  }
  // Quote every text cell, and neutralize spreadsheet formulas in text only (not negative numbers).
  const safe = /^[\s\uFEFF]*[=+\-@]/u.test(value) || /^[\t\r\n]/u.test(value) ? `'${value}` : value
  return `"${safe.replaceAll('"', '""')}"`
}

interface ExportMetric {
  key: string
  project: number | null
  heading: string
  value: (experiment: ComparisonExperiment) => number | null
  bestIds: number[]
}

function exportMetrics(result: ExperimentCompareResponse): ExportMetric[] {
  const builtin: { key: MetricName; label: string }[] = [
    { key: 'accuracy', label: 'Accuracy' }, { key: 'precision', label: 'Precision' },
    { key: 'recall', label: 'Recall' }, { key: 'f1', label: 'F1' }, { key: 'loss', label: 'Loss' },
  ]
  return [
    ...(result.custom_metrics ?? []).map(metric => ({
      key: metric.definition.key, project: metric.definition.project_id,
      heading: `项目 #${metric.definition.project_id} ${metric.project_name} / ${metric.definition.name} [${metric.definition.key}]${metric.definition.unit ? ` (${metric.definition.unit})` : ''} ${metric.definition.direction === 'max' ? '↑ 越大越好' : '↓ 越小越好'}`,
      value: (experiment: ComparisonExperiment) => experiment.project_id === metric.definition.project_id && experiment.result !== null ? metric.values[experiment.id] ?? null : null,
      bestIds: metric.best.experiment_ids,
    })),
    ...builtin.map(metric => ({
      key: metric.key, project: null,
      heading: `${metric.label} [${metric.key}] ${result.best_by_metric[metric.key].direction === 'max' ? '↑ 越大越好' : '↓ 越小越好'}`,
      value: (experiment: ComparisonExperiment) => experiment.result?.[metric.key] ?? null,
      bestIds: result.best_by_metric[metric.key].experiment_ids,
    })),
  ]
}

export function buildComparisonCsv(snapshot: ComparisonExportSnapshot): string {
  const { result } = snapshot
  const metrics = exportMetrics(result)
  const metadata = new Map(snapshot.metadata.map(item => [item.id, item]))
  const baseline = result.baseline_comparison
  const baselineExperiment = result.experiments.find(item => item.id === baseline?.baseline_experiment_id)
  const deltas = new Map((baseline?.metrics ?? []).map(metric => [`${metric.project_id ?? 'system'}:${metric.key}`, metric]))
  const headers: CsvCell[] = ['实验 ID', '实验编号', '模型名称', '项目 ID', '项目名称', '批次 ID', '批次名称', '结果状态', '数据获取时间 (UTC)', '文件导出时间 (UTC)']
  if (baseline) headers.push('基准实验 ID', '基准实验编号', '是否基准')
  for (const metric of metrics) {
    headers.push(`${metric.heading} / 原始值`, `${metric.heading} / 指标状态`, `${metric.heading} / 是否最佳`)
    if (baseline) headers.push(`${metric.heading} / 绝对差值`, `${metric.heading} / 差值状态`, `${metric.heading} / 无法比较原因`)
  }
  const rows: CsvCell[][] = [headers]
  for (const experiment of result.experiments) {
    const names = metadata.get(experiment.id)
    const row: CsvCell[] = [experiment.id, experiment.experiment_no, experiment.model_name,
      experiment.project_id, names?.project_id === experiment.project_id ? names.project_name : `Project #${experiment.project_id}`,
      experiment.batch_id, names?.batch_id === experiment.batch_id ? names.batch_name : `Batch #${experiment.batch_id}`,
      experiment.result === null ? '未录入结果' : '已录入结果', snapshot.fetchedAt, snapshot.exportedAt]
    if (baseline) row.push(baseline.baseline_experiment_id, baselineExperiment?.experiment_no ?? '', experiment.id === baseline.baseline_experiment_id ? '是' : '否')
    for (const metric of metrics) {
      const value = metric.value(experiment)
      const applicable = metric.project === null || metric.project === experiment.project_id
      row.push(value, !applicable ? '不适用（其他项目）' : experiment.result === null ? '未录入结果' : value === null ? '缺失指标' : '有值',
        value === null ? null : metric.bestIds.includes(experiment.id) ? '是' : '否')
      if (baseline) {
        const delta: MetricDelta | undefined = deltas.get(`${metric.project ?? 'system'}:${metric.key}`)?.comparisons[experiment.id]
        row.push(delta?.delta ?? null, deltaStatusLabels[delta?.status ?? 'unavailable'], delta?.reason ? deltaReasonLabels[delta.reason] : delta ? '' : '未提供差值')
      }
    }
    rows.push(row)
  }
  return '\uFEFF' + rows.map(row => row.map(csvCell).join(',')).join('\r\n') + '\r\n'
}

export function exportFilename(kind: string, exportedAt: string, extension: 'csv' | 'png'): string {
  const safe = kind.replace(/[<>:"/\\|?*\u0000-\u001F]/g, '_').slice(0, 80)
  const stamp = exportedAt.replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z')
  return `AIExpHub_${safe}_${stamp}.${extension}`
}

/** One refreshed snapshot per file. Cancellation is rechecked after async image generation. */
export async function runComparisonExport<T>(options: {
  refresh: () => Promise<ComparisonExportSnapshot | null>
  isCurrent: () => boolean
  generate: (snapshot: ComparisonExportSnapshot) => T | Promise<T>
  deliver: (artifact: T, snapshot: ComparisonExportSnapshot) => void
}): Promise<boolean> {
  const snapshot = await options.refresh()
  if (!snapshot) return false
  const assertCurrent = () => { if (!options.isCurrent()) throw new Error('比较内容已变化，本次导出已取消，请重新比较后导出。') }
  assertCurrent()
  const artifact = await options.generate(snapshot)
  assertCurrent()
  options.deliver(artifact, snapshot)
  return true
}
