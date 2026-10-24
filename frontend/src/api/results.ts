import client from './client'
import { publishComparisonChange } from '../utils/comparison-changes'

export interface ExperimentResult {
  id: number
  experiment_id: number
  accuracy: number | null
  precision: number | null
  recall: number | null
  f1: number | null
  loss: number | null
  updated_at: string
  custom_metrics?: Record<string, number>
}

export interface ResultPayload {
  accuracy?: number | null
  precision?: number | null
  recall?: number | null
  f1?: number | null
  loss?: number | null
  custom_metrics?: Record<string, number | null>
}

export type BuiltinMetric = 'accuracy' | 'precision' | 'recall' | 'f1' | 'loss'
export type ResultMetric = string

export async function getExperimentResult(experimentId: number): Promise<ExperimentResult> {
  return (await client.get<ExperimentResult>(`/experiments/${experimentId}/result`)).data
}

export async function createExperimentResult(experimentId: number, payload: ResultPayload): Promise<ExperimentResult> {
  const saved = (await client.post<ExperimentResult>(`/experiments/${experimentId}/result`, payload)).data
  publishComparisonChange({ kind: 'experiment', id: experimentId })
  return saved
}

export async function updateExperimentResult(experimentId: number, payload: ResultPayload): Promise<ExperimentResult> {
  const saved = (await client.put<ExperimentResult>(`/experiments/${experimentId}/result`, payload)).data
  publishComparisonChange({ kind: 'experiment', id: experimentId })
  return saved
}
