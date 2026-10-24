import type { MetricDiscovery } from './json-metrics'

export interface MappingMetric {
  id: number | null; key: string; builtin: boolean
}
export interface MappingBinding {
  metric_key: string; metric_id: number | null; builtin: boolean; pointer: string
}
export interface MappingTemplate {
  id: number; project_id: number; name: string; mappings: MappingBinding[]
}

export function templateChoices(template: MappingTemplate, metrics: MappingMetric[], discovery: MetricDiscovery) {
  const choices: Record<string, string | null> = Object.fromEntries(metrics.map(metric => [metric.key, '']))
  const missing: string[] = []
  const arrayBlocked = new Set<string>()
  for (const binding of template.mappings) {
    const metric = metrics.find(item => binding.builtin
      ? item.builtin && item.key === binding.metric_key
      : !item.builtin && binding.metric_id !== null && item.id === binding.metric_id)
    if (!metric) { missing.push(binding.metric_key); continue }
    choices[metric.key] = binding.pointer
    if (discovery.fields.find(field => field.pointer === binding.pointer)?.arrayPath) arrayBlocked.add(metric.key)
  }
  return { choices, missing, arrayBlocked }
}

export function captureMappings(metrics: MappingMetric[], discovery: MetricDiscovery, choices: Record<string, string | null>): MappingBinding[] {
  const result: MappingBinding[] = []
  for (const metric of metrics) {
    const pointer = choices[metric.key]
    if (pointer === '') continue
    const field = discovery.fields.find(item => item.pointer === pointer)
    if (!field) throw new Error('请先修正缺失或未确认的路径。')
    if (field.arrayPath) throw new Error('含数组下标的路径不能保存为复用模板；本次仍可手动映射录入。')
    result.push({ metric_key: metric.key, metric_id: metric.id, builtin: metric.builtin, pointer: field.pointer })
  }
  if (!result.length) throw new Error('至少映射一个指标后才能保存模板。')
  return result
}
