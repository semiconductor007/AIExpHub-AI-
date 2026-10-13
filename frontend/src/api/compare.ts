import client from './client'
import type { MetricDefinition } from './metrics'

export interface ComparisonResultMetrics {
  accuracy: number | null
  precision: number | null
  recall: number | null
  f1: number | null
  loss: number | null
  custom_metrics?: Record<string, number>
}

export interface ComparisonExperiment {
  id: number
  experiment_no: string
  model_name: string
  batch_id: number
  project_id: number
  result: ComparisonResultMetrics | null
}

export type MetricName = 'accuracy' | 'precision' | 'recall' | 'f1' | 'loss'

export interface BestMetric {
  direction: 'max' | 'min'
  value: number | null
  experiment_ids: number[]
}

export interface ComparisonBestByMetric {
  accuracy: BestMetric
  precision: BestMetric
  recall: BestMetric
  f1: BestMetric
  loss: BestMetric
}

export interface ExperimentCompareResponse {
  experiments: ComparisonExperiment[]
  best_by_metric: ComparisonBestByMetric
  custom_metrics?: CustomMetricComparison[]
  baseline_comparison?: BaselineComparison
}

export interface MetricDelta {
  delta: number | null
  status: 'improved' | 'regressed' | 'unchanged' | 'unavailable'
  reason: 'baseline_project_mismatch' | 'experiment_project_mismatch' | 'baseline_result_missing'
    | 'experiment_result_missing' | 'baseline_metric_missing' | 'experiment_metric_missing' | 'overflow' | null
}

export interface BaselineMetricComparison {
  key: string
  project_id: number | null
  name: string
  unit: string
  direction: 'max' | 'min'
  baseline_value: number | null
  comparisons: Record<number, MetricDelta>
}

export interface BaselineComparison {
  baseline_experiment_id: number
  metrics: BaselineMetricComparison[]
}

export interface CustomMetricComparison {
  definition: MetricDefinition
  project_name: string
  values: Record<number, number | null>
  best: BestMetric
}

export interface ExperimentCompareRequest {
  experiment_ids: number[]
  baseline_experiment_id?: number
}

export async function compareExperiments(experimentIds: number[], baselineId: number | null = null): Promise<ExperimentCompareResponse> {
  const payload: ExperimentCompareRequest = { experiment_ids: experimentIds }
  if (baselineId !== null) payload.baseline_experiment_id = baselineId
  return (await client.post<ExperimentCompareResponse>('/experiments/compare', payload)).data
}
