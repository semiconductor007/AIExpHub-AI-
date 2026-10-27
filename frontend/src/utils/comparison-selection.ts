/** Keep shareable comparison links limited to distinct, positive database IDs. */
export function comparisonIds(value: unknown): number[] {
  if (value === undefined || value === null || value === '') return []
  if (typeof value !== 'string') throw new Error('比较链接中的实验编号无效。')
  const parts = value.split(',')
  if (parts.some(part => !/^[1-9]\d*$/.test(part) || !Number.isSafeInteger(Number(part)))) {
    throw new Error('比较链接中的实验编号无效。')
  }
  return [...new Set(parts.map(Number))]
}

export function comparisonQuery(ids: number[], baseline: number | null = null): Record<string, string> {
  const distinct = [...new Set(ids)]
  return {
    ...(distinct.length ? { ids: distinct.join(',') } : {}),
    ...(baseline !== null && distinct.includes(baseline) ? { baseline: String(baseline) } : {}),
  }
}
