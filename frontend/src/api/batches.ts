import client from './client'

export interface ExperimentBatch {
  id: number
  project_id: number
  name: string
  description: string | null
  created_at: string
}

export interface BatchPayload {
  name: string
  description?: string | null
}

export async function getProjectBatches(projectId: number): Promise<ExperimentBatch[]> {
  return (await client.get<ExperimentBatch[]>(`/projects/${projectId}/batches`)).data
}

export async function getBatch(batchId: number): Promise<ExperimentBatch> {
  return (await client.get<ExperimentBatch>(`/batches/${batchId}`)).data
}

export async function createBatch(projectId: number, payload: BatchPayload): Promise<ExperimentBatch> {
  return (await client.post<ExperimentBatch>(`/projects/${projectId}/batches`, payload)).data
}

export async function updateBatch(batchId: number, payload: BatchPayload): Promise<ExperimentBatch> {
  return (await client.put<ExperimentBatch>(`/batches/${batchId}`, payload)).data
}

export async function deleteBatch(batchId: number): Promise<void> {
  await client.delete(`/batches/${batchId}`)
}
