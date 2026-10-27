import type { EChartsCoreOption } from 'echarts/core'

export type ChartExportTarget = { kind: 'comprehensive' | 'loss' } | { kind: 'custom'; projectId: number; key: string }
export interface ChartExportSpec {
  option: EChartsCoreOption
  title: string
  description: string
  labels: string[]
  filename: string
}

export function wrapChartLabel(label: string, columns = 16): string {
  const characters = Array.from(label)
  const lines: string[] = []
  for (let index = 0; index < characters.length; index += columns) lines.push(characters.slice(index, index + columns).join(''))
  return lines.join('\n')
}

export function chartExportLayout(labels: string[]) {
  const width = Math.max(1000, labels.length * 240)
  const lines = Math.max(1, ...labels.map(label => wrapChartLabel(label).split('\n').length))
  const bottom = lines * 20 + 28
  const height = 420 + bottom
  // Bound temporary canvas memory and avoid silently squeezing or truncating experiment labels.
  if (width > 8192 || width * (height + 300) * 4 > 32_000_000) {
    throw new Error('图表内容超出图片尺寸限制，请减少单次导出的实验数量，或使用 CSV 导出完整数据。')
  }
  return { width, height, bottom }
}
