import client from './client'
import type { MetricDelta } from './compare'

export interface SummarySelection {
  experiment_ids: number[]
  baseline_experiment_id: number | null
  primary_metric: string | null
  parameter_paths: string[]
}
export interface SummaryExperiment {
  id: number; experiment_no: string; model_name: string; project_id: number; batch_id: number
  has_result: boolean
  parameters: Record<string, { present: boolean; value: unknown }>
}
export interface SummaryFact {
  id: string; key: string; name: string; unit: string; direction: 'max' | 'min'
  values: Record<string, number | null>
  best: { value: number | null; experiment_ids: number[] }
  baseline: { comparisons: Record<string, MetricDelta> } | null
}
export interface SummaryData {
  experiment_ids: number[]; baseline_experiment_id: number | null; primary_metric: string | null
  warnings: string[]
  evidence: { id: string; experiment_ids: number[]; metric_ids: string[]; data: SummaryExperiment | SummaryFact }[]
}
export interface SummaryPreview {
  fingerprint: string; fetched_at: string; data: SummaryData; facts: SummaryFact[]
  parameter_paths: string[]
  metric_options: { id: string; name: string; unit: string; comparable: boolean }[]
  messages: { role: string; content: string }[]
  configured_model: string
}
export interface AISummary {
  fingerprint: string; fetched_at: string; generated_at: string; model: string; stale: boolean
  facts: SummaryFact[]; data: SummaryData
  narrative: { sections: { key: string; items: {
    kind: 'observation' | 'hypothesis' | 'suggestion'; text: string
    experiment_ids: number[]; metric_ids: string[]; evidence_ids: string[]
  }[] }[] }
}
export interface SummaryStatus { ready: boolean; message: string; max_experiments: number }

export async function getSummaryStatus(signal?: AbortSignal): Promise<SummaryStatus> {
  return (await client.get<SummaryStatus>('/ai/summaries/status', { signal })).data
}
export async function previewSummary(selection: SummarySelection, signal?: AbortSignal): Promise<SummaryPreview> {
  return (await client.post<SummaryPreview>('/ai/summaries/preview', selection, { signal })).data
}
export async function checkSummary(selection: SummarySelection, fingerprint: string, signal?: AbortSignal): Promise<boolean> {
  return (await client.post<{ current: boolean }>('/ai/summaries/check', { ...selection, fingerprint }, { signal })).data.current
}
export async function generateSummary(selection: SummarySelection, fingerprint: string, requestId: string, signal?: AbortSignal): Promise<AISummary> {
  return (await client.post<AISummary>('/ai/summaries/generate', { ...selection, fingerprint, request_id: requestId }, {
    signal, timeout: 135_000,
  })).data
}
