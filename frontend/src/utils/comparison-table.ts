import type { ComparisonExperiment, ExperimentCompareResponse, MetricDelta, MetricName } from '../api/compare'

export interface ComparisonCell {
  value: number | null
  status: 'value' | 'missing' | 'no-result' | 'not-applicable'
  best: boolean
  delta?: MetricDelta
}

export interface ComparisonMetricRow {
  id: string
  key: string
  name: string
  unit: string
  direction: 'max' | 'min'
  projectId: number | null
  projectName: string
  cells: Record<number, ComparisonCell>
  hasData: boolean
  bestIds: number[]
}

export function comparisonMetricRows(result: ExperimentCompareResponse): ComparisonMetricRow[] {
  const builtin: { key: MetricName; name: string }[] = [
    { key: 'accuracy', name: 'Accuracy' }, { key: 'precision', name: 'Precision' },
    { key: 'recall', name: 'Recall' }, { key: 'f1', name: 'F1' }, { key: 'loss', name: 'Loss' },
  ]
  const deltas = new Map((result.baseline_comparison?.metrics ?? []).map(item => [`${item.project_id ?? 'system'}:${item.key}`, item.comparisons]))
  const definitions = [
    ...builtin.map(item => ({ ...item, id: `system:${item.key}`, unit: '', projectId: null as number | null,
      projectName: '', best: result.best_by_metric[item.key], value: (e: ComparisonExperiment) => e.result?.[item.key] ?? null })),
    ...(result.custom_metrics ?? []).map(item => ({ id: `custom:${item.definition.project_id}:${item.definition.id ?? item.definition.key}`,
      key: item.definition.key, name: item.definition.name, unit: item.definition.unit,
      projectId: item.definition.project_id, projectName: item.project_name, best: item.best,
      value: (e: ComparisonExperiment) => item.values[e.id] ?? null })),
  ]
  return definitions.map(metric => {
    const cells: Record<number, ComparisonCell> = {}
    for (const experiment of result.experiments) {
      const applicable = metric.projectId === null || metric.projectId === experiment.project_id
      const value = applicable && experiment.result !== null ? metric.value(experiment) : null
      cells[experiment.id] = { value,
        status: !applicable ? 'not-applicable' : experiment.result === null ? 'no-result' : value === null ? 'missing' : 'value',
        best: value !== null && metric.best.experiment_ids.includes(experiment.id),
        delta: deltas.get(`${metric.projectId ?? 'system'}:${metric.key}`)?.[experiment.id],
      }
    }
    return { id: metric.id, key: metric.key, name: metric.name, unit: metric.unit,
      direction: metric.best.direction, projectId: metric.projectId, projectName: metric.projectName,
      cells, hasData: Object.values(cells).some(cell => cell.value !== null), bestIds: [...metric.best.experiment_ids] }
  })
}

export function filterComparisonMetrics(rows: ComparisonMetricRow[], excludedIds: string[], query: string, hideEmpty: boolean): ComparisonMetricRow[] {
  const search = query.trim().toLocaleLowerCase()
  return rows.filter(row => !excludedIds.includes(row.id) && (!hideEmpty || row.hasData)
    && (!search || `${row.name} ${row.key} ${row.unit} ${row.projectName}`.toLocaleLowerCase().includes(search)))
}

export function experimentColumnCapacity(width: number, hasBaseline: boolean): number {
  const metricWidth = Math.max(96, Math.min(180, width * .25))
  return Math.max(hasBaseline ? 2 : 1, Math.min(4, Math.floor((width - metricWidth) / 200)))
}

/** Pages change presentation only; ranking always comes from the full API response. */
export function comparisonExperimentPage(experiments: ComparisonExperiment[], baselineId: number | undefined, capacity: number, requestedPage: number) {
  const baseline = experiments.find(item => item.id === baselineId)
  const others = experiments.filter(item => item.id !== baseline?.id)
  const size = Math.max(1, Math.floor(capacity) - (baseline ? 1 : 0))
  const pageCount = Math.max(1, Math.ceil(others.length / size))
  const page = Math.max(1, Math.min(pageCount, Math.floor(requestedPage) || 1))
  const offset = (page - 1) * size
  const items = others.slice(offset, offset + size)
  return { experiments: baseline ? [baseline, ...items] : items, page, pageCount, offset, otherCount: others.length,
    first: others.length ? offset + 1 : 0, last: Math.min(others.length, offset + size), baselineId: baseline?.id }
}
