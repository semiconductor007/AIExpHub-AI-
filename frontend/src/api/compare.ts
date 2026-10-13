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
}

export interface CustomMetricComparison {
  definition: MetricDefinition
  project_name: string
  values: Record<number, number | null>
  best: BestMetric
}

export interface ExperimentCompareRequest {
  experiment_ids: number[]
}

export async function compareExperiments(experimentIds: number[]): Promise<ExperimentCompareResponse> {
  const payload: ExperimentCompareRequest = { experiment_ids: experimentIds }
  return (await client.post<ExperimentCompareResponse>('/experiments/compare', payload)).data
}
