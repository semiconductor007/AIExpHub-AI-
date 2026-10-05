import client from './client'

export interface ExperimentResult {
  id: number
  experiment_id: number
  accuracy: number | null
  precision: number | null
  recall: number | null
  f1: number | null
  loss: number | null
  updated_at: string
}

export interface ResultPayload {
  accuracy?: number | null
  precision?: number | null
  recall?: number | null
  f1?: number | null
  loss?: number | null
}

export type ResultMetric = 'accuracy' | 'precision' | 'recall' | 'f1' | 'loss'

export async function getExperimentResult(experimentId: number): Promise<ExperimentResult> {
  return (await client.get<ExperimentResult>(`/experiments/${experimentId}/result`)).data
}

export async function createExperimentResult(experimentId: number, payload: ResultPayload): Promise<ExperimentResult> {
  return (await client.post<ExperimentResult>(`/experiments/${experimentId}/result`, payload)).data
}

export async function updateExperimentResult(experimentId: number, payload: ResultPayload): Promise<ExperimentResult> {
  return (await client.put<ExperimentResult>(`/experiments/${experimentId}/result`, payload)).data
}
