export const MAX_JSON_BYTES = 1024 * 1024

export function parseJsonText(text: string): unknown {
  const value: unknown = JSON.parse(text.replace(/^\uFEFF/, ''))
  function check(item: unknown): void {
    if (typeof item === 'number' && !Number.isFinite(item)) throw new Error('JSON 不能包含超出有限数值范围的数字。')
    if (typeof item === 'object' && item !== null) for (const child of Object.values(item)) check(child)
  }
  check(value)
  return value
}

export async function readJsonFile(file: File): Promise<string> {
  if (!file.name.toLowerCase().endsWith('.json')) throw new Error('请选择 .json 文件。')
  if (file.size > MAX_JSON_BYTES) throw new Error('JSON 文件不能超过 1 MiB，请拆分后导入。')
  const text = (await file.text()).replace(/^\uFEFF/, '')
  // Validate before replacing the existing editable draft.
  parseJsonText(text)
  return text
}

export function downloadJson(value: unknown, filename: string): void {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: 'application/json;charset=utf-8' }))
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
