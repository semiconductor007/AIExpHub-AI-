export type ParameterValueType = 'text' | 'number' | 'boolean' | 'json'

export interface ParameterRowValue {
  key: string
  type: ParameterValueType
  value: string
}

export interface ParameterTypeOption {
  label: string
  value: ParameterValueType
}

export const parameterTypeOptions: ParameterTypeOption[] = [
  { label: '文本', value: 'text' },
  { label: '数字', value: 'number' },
  { label: '布尔值', value: 'boolean' },
  { label: 'JSON', value: 'json' },
]

export function isParameterObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

export function parseParameterObject(text: string, allowEmpty = false): Record<string, unknown> {
  let value: unknown
  try {
    value = JSON.parse(text)
  } catch {
    throw new Error('实验参数必须是合法的 JSON 对象。')
  }
  if (!isParameterObject(value) || (!allowEmpty && Object.keys(value).length === 0)) {
    throw new Error(allowEmpty ? '实验参数必须是 JSON 对象。' : '实验参数必须是非空 JSON 对象。')
  }
  return value
}

export function parameterRowsFromObject(parameters: Record<string, unknown>): ParameterRowValue[] {
  return Object.entries(parameters).map(([key, value]) => {
    if (typeof value === 'string') return { key, type: 'text', value }
    if (typeof value === 'number' && Number.isFinite(value)) return { key, type: 'number', value: String(value) }
    if (typeof value === 'boolean') return { key, type: 'boolean', value: String(value) }
    return { key, type: 'json', value: JSON.stringify(value) ?? 'null' }
  })
}

function parseRowValue(row: ParameterRowValue): unknown {
  if (row.type === 'text') return row.value
  if (row.type === 'number') {
    if (!row.value.trim()) throw new Error(`参数“${row.key || '未命名'}”的数字值不能为空。`)
    const value = Number(row.value)
    if (!Number.isFinite(value)) throw new Error(`参数“${row.key || '未命名'}”必须是有限数字。`)
    return value
  }
  if (row.type === 'boolean') {
    if (row.value === 'true') return true
    if (row.value === 'false') return false
    throw new Error(`参数“${row.key || '未命名'}”请选择 true 或 false。`)
  }
  try {
    return JSON.parse(row.value)
  } catch {
    throw new Error(`参数“${row.key || '未命名'}”的 JSON 值无效。`)
  }
}

export function parameterRowsToObject(rows: ParameterRowValue[]): Record<string, unknown> {
  const parameters = Object.create(null) as Record<string, unknown>
  const keys = new Set<string>()
  for (const row of rows) {
    const key = row.key.trim()
    if (!key) throw new Error('参数名不能为空。')
    if (keys.has(key)) throw new Error(`参数名“${key}”重复。`)
    keys.add(key)
    parameters[key] = parseRowValue({ ...row, key })
  }
  return parameters
}

export function formatParameterObject(parameters: Record<string, unknown>): string {
  return JSON.stringify(parameters, null, 2)
}
