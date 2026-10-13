import client from './client'
import type { Experiment } from './experiments'

export interface ImportDocument {
  format_version?: 1
  project_id?: number | null
  metric_definitions?: unknown[]
  experiments: unknown[]
}

export interface ImportPreview {
  can_import: boolean
  total: number
  valid_count: number
  rows: { row: number; experiment_no: string | null; normalized: Record<string, unknown> | null; errors: string[] }[]
}

export async function getImportTemplate(projectId: number): Promise<ImportDocument> {
  return (await client.get<ImportDocument>(`/projects/${projectId}/import-template`)).data
}

export async function previewImport(batchId: number, document: ImportDocument): Promise<ImportPreview> {
  return (await client.post<ImportPreview>(`/batches/${batchId}/imports/preview`, document)).data
}

export async function confirmImport(batchId: number, document: ImportDocument): Promise<Experiment[]> {
  return (await client.post<Experiment[]>(`/batches/${batchId}/imports`, document)).data
}
