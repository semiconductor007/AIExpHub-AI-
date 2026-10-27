import { init } from 'echarts/core'
import type { EChartsType } from 'echarts/core'
import type { ChartExportSpec } from './chart-export-layout'
import { chartExportLayout, wrapChartLabel } from './chart-export-layout'

function wrappedLines(context: CanvasRenderingContext2D, value: string, width: number): string[] {
  const lines: string[] = []
  let line = ''
  for (const character of value) {
    if (character === '\n' || context.measureText(line + character).width > width) {
      lines.push(line); line = character === '\n' ? '' : character
    } else line += character
  }
  lines.push(line)
  return lines
}

export async function createChartPng(spec: ChartExportSpec, fetchedAt: string, exportedAt: string): Promise<Blob> {
  const layout = chartExportLayout(spec.labels)
  await document.fonts.ready
  const host = document.createElement('div')
  Object.assign(host.style, { position: 'fixed', left: '-100000px', top: '0', width: `${layout.width}px`, height: `${layout.height}px` })
  host.setAttribute('aria-hidden', 'true')
  document.body.append(host)
  let chart: EChartsType | undefined
  try {
    chart = init(host, undefined, { renderer: 'canvas', width: layout.width, height: layout.height })
    const option = spec.option as Record<string, unknown>
    const axis = option.xAxis as Record<string, unknown>
    chart.setOption({ ...option, animation: false,
      grid: { ...(option.grid as object), bottom: layout.bottom, left: 84, right: 40 },
      xAxis: { ...axis, axisLabel: { interval: 0, rotate: 0, fontSize: 13, lineHeight: 20, formatter: (value: string) => wrapChartLabel(value) } },
    }, { notMerge: true })
    const image = new Image()
    image.src = chart.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#fff' })
    await image.decode()
    const canvas = document.createElement('canvas')
    const context = canvas.getContext('2d')
    if (!context) throw new Error('浏览器无法生成图片，请使用 CSV 导出或换用支持 Canvas 的浏览器。')
    context.font = 'bold 22px "Microsoft YaHei", sans-serif'
    const titles = wrappedLines(context, spec.title, layout.width - 64)
    context.font = '14px "Microsoft YaHei", sans-serif'
    const descriptions = wrappedLines(context, spec.description, layout.width - 64)
    const header = 32 + titles.length * 32 + descriptions.length * 24 + 26
    const totalHeight = header + layout.height + 64
    if (layout.width * totalHeight * 4 > 32_000_000) throw new Error('图片内容过长，请缩短指标名称或使用 CSV 导出。')
    canvas.width = layout.width * 2; canvas.height = totalHeight * 2
    context.scale(2, 2)
    context.fillStyle = '#fff'; context.fillRect(0, 0, layout.width, totalHeight)
    context.fillStyle = '#111827'; context.font = 'bold 22px "Microsoft YaHei", sans-serif'
    let y = 34
    for (const line of titles) { context.fillText(line, 32, y); y += 32 }
    context.font = '14px "Microsoft YaHei", sans-serif'; context.fillStyle = '#4b5563'
    for (const line of descriptions) { context.fillText(line, 32, y); y += 24 }
    context.drawImage(image, 0, header, layout.width, layout.height)
    context.font = '13px "Microsoft YaHei", sans-serif'; context.fillStyle = '#4b5563'
    context.fillText(`AIExpHub | 数据获取：${fetchedAt} | 导出：${exportedAt}`, 32, totalHeight - 26)
    const blob = await new Promise<Blob | null>(resolve => canvas.toBlob(resolve, 'image/png'))
    if (!blob) throw new Error('图片生成失败，请重试。')
    return blob
  } finally { chart?.dispose(); host.remove() }
}
