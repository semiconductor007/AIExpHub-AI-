/** Inspect a result document without modifying it or guessing metric aliases. */
export interface MetricRule {
  key: string
  name: string
  lower_bound: number | null
  upper_bound: number | null
}

export interface JsonField {
  pointer: string
  path: string
  key: string | null
  value: unknown
  leaf: boolean
}

export interface MetricDiscovery {
  fields: JsonField[]
  candidates: Map<string, JsonField[]>
  simple: boolean
}

export function inspectMetricJson(text: string, metrics: MetricRule[]): MetricDiscovery {
  if (new Blob([text]).size > 1024 * 1024) throw new Error('JSON 内容不能超过 1 MiB，请只保留需要的结果片段。')
  const root: unknown = JSON.parse(text.replace(/^\uFEFF/, ''))
  if (typeof root !== 'object' || root === null) throw new Error('结果 JSON 必须是对象或记录数组。')
  const keys = new Set(metrics.map(metric => metric.key))
  const candidates = new Map(metrics.map(metric => [metric.key, [] as JsonField[]]))
  const fields: JsonField[] = []
  const stack: (Omit<JsonField, 'leaf'> & { depth: number })[] = [{ value: root, pointer: '', path: '$', key: null, depth: 0 }]
  let visited = 0
  while (stack.length) {
    const node = stack.pop()!
    if (++visited > 100_000 || node.depth > 100) throw new Error('JSON 结构过大或嵌套过深，请只保留需要的结果子对象。')
    const leaf = node.value === null || typeof node.value !== 'object'
    const field: JsonField = { pointer: node.pointer, path: node.path, key: node.key, value: node.value, leaf }
    const matches = node.key !== null && keys.has(node.key)
    if (leaf || matches) {
      fields.push(field)
      if (fields.length > 20_000) throw new Error('JSON 字段过多，请只保留需要的结果子对象。')
    }
    if (matches) candidates.get(node.key!)!.push(field)
    if (!leaf) {
      const entries = Object.entries(node.value as Record<string, unknown>)
      if (entries.length + visited + stack.length > 100_000) throw new Error('JSON 结构过大，请只保留需要的结果子对象。')
      for (let index = entries.length - 1; index >= 0; index -= 1) {
        const [key, value] = entries[index]!
        const token = key.replace(/~/g, '~0').replace(/\//g, '~1')
        const suffix = Array.isArray(node.value) ? `[${key}]` : /^[a-zA-Z_$][\w$]*$/.test(key) ? `.${key}` : `[${JSON.stringify(key)}]`
        stack.push({ value, pointer: `${node.pointer}/${token}`, path: node.path + suffix,
          key: Array.isArray(node.value) ? null : key, depth: node.depth + 1 })
      }
    }
  }
  return { fields, candidates, simple: !Array.isArray(root) && Object.entries(root).every(([key, value]) => keys.has(key) && (value === null || typeof value !== 'object')) }
}

export function defaultMetricChoices(discovery: MetricDiscovery, metrics: MetricRule[]): Record<string, string | null> {
  return Object.fromEntries(metrics.map(metric => {
    const matches = discovery.candidates.get(metric.key) ?? []
    return [metric.key, matches.length === 1 ? matches[0]!.pointer : matches.length > 1 ? null : '']
  }))
}

export function validateMetricChoices(discovery: MetricDiscovery, metrics: MetricRule[], choices: Record<string, string | null>) {
  const fields = new Map(discovery.fields.map(field => [field.pointer, field]))
  const values: Record<string, number | null> = {}
  const errors: Record<string, string> = {}
  const used = new Set<string>()
  for (const metric of metrics) {
    const pointer = choices[metric.key]
    if (pointer === '') continue // Explicitly omit this metric; no source value is guessed.
    if (pointer === null || pointer === undefined) {
      errors[metric.key] = '发现多个候选，请选择一个字段或明确不映射。'
      continue
    }
    const field = fields.get(pointer)
    if (!field) { errors[metric.key] = '所选字段不存在，请重新选择。'; continue }
    const value = field.value
    if (value !== null && (typeof value !== 'number' || !Number.isFinite(value))) {
      errors[metric.key] = '必须是有限数值或 null，不接受文本、布尔值、对象或数组。'
    } else if (typeof value === 'number' && ((metric.lower_bound !== null && value < metric.lower_bound)
               || (metric.upper_bound !== null && value > metric.upper_bound))) {
      errors[metric.key] = `超出项目范围 [${metric.lower_bound ?? '不限'}, ${metric.upper_bound ?? '不限'}]。`
    } else {
      values[metric.key] = value as number | null
      used.add(pointer)
    }
  }
  const hasValue = Object.values(values).some(value => value !== null)
  return { values, errors, used, canApply: hasValue && !Object.keys(errors).length,
    message: hasValue ? '' : '至少选择一项有效数值；可手动映射其他字段，或清空 JSON 后手动录入。' }
}

export function jsonValueLabel(value: unknown): string {
  if (value === null) return 'null（空值）'
  if (typeof value === 'string') return `${JSON.stringify(value.length > 60 ? value.slice(0, 60) + '…' : value)}（文本）`
  if (typeof value === 'boolean') return `${value}（布尔值）`
  if (typeof value === 'number') return Number.isFinite(value) ? String(value) : '非有限数值'
  return Array.isArray(value) ? `数组（${value.length} 项）` : '对象'
}
