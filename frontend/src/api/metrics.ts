import client from './client'
import { publishComparisonChange } from '../utils/comparison-changes'

export interface MetricDefinition {
  id: number | null
  project_id: number
  key: string
  name: string
  unit: string
  direction: 'max' | 'min'
  lower_bound: number | null
  upper_bound: number | null
  builtin: boolean
}

export type MetricDefinitionPayload = Pick<MetricDefinition, 'key' | 'name' | 'unit' | 'direction' | 'lower_bound' | 'upper_bound'>
export async function getProjectMetrics(projectId: number): Promise<MetricDefinition[]> {
  return (await client.get<MetricDefinition[]>(`/projects/${projectId}/metrics`)).data
}
export async function createProjectMetric(projectId: number, payload: MetricDefinitionPayload): Promise<MetricDefinition> {
  const saved = (await client.post<MetricDefinition>(`/projects/${projectId}/metrics`, payload)).data
  publishComparisonChange({ kind: 'project-metrics', id: projectId })
  return saved
}
export async function updateProjectMetric(projectId: number, id: number, payload: MetricDefinitionPayload): Promise<MetricDefinition> {
  const saved = (await client.put<MetricDefinition>(`/projects/${projectId}/metrics/${id}`, payload)).data
  publishComparisonChange({ kind: 'project-metrics', id: projectId })
  return saved
}
export async function deleteProjectMetric(projectId: number, id: number): Promise<void> {
  await client.delete(`/projects/${projectId}/metrics/${id}`)
  publishComparisonChange({ kind: 'project-metrics', id: projectId })
}
export function metricLabel(metric: Pick<MetricDefinition, 'name' | 'unit'>): string {
  return metric.unit ? `${metric.name}（${metric.unit}）` : metric.name
}
