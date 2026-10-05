import client from './client'

export interface Experiment {
  id: number
  batch_id: number
  experiment_no: string
  model_name: string
  parameters: Record<string, unknown>
  created_at: string
  notes: string | null
}

export interface ExperimentPayload {
  experiment_no: string
  model_name: string
  parameters: Record<string, unknown>
  notes?: string | null
}

export async function getBatchExperiments(batchId: number): Promise<Experiment[]> {
  return (await client.get<Experiment[]>(`/batches/${batchId}/experiments`)).data
}

export async function getExperiment(experimentId: number): Promise<Experiment> {
  return (await client.get<Experiment>(`/experiments/${experimentId}`)).data
}

export async function createExperiment(batchId: number, payload: ExperimentPayload): Promise<Experiment> {
  return (await client.post<Experiment>(`/batches/${batchId}/experiments`, payload)).data
}

export async function updateExperiment(experimentId: number, payload: ExperimentPayload): Promise<Experiment> {
  return (await client.put<Experiment>(`/experiments/${experimentId}`, payload)).data
}

export async function deleteExperiment(experimentId: number): Promise<void> {
  await client.delete(`/experiments/${experimentId}`)
}
