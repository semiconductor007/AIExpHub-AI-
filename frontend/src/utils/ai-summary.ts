import type { AISummary, SummaryData, SummaryExperiment, SummaryFact } from '../api/ai-summaries'

export const sectionLabels: Record<string, string> = {
  overview: '实验概况', metrics: '指标表现', parameters: '参数差异解释', limitations: '局限与权衡', next_steps: '下一步建议',
}
export const kindLabels = { observation: '观察', hypothesis: '待验证推测', suggestion: '建议' }

export function summaryExperiments(data: SummaryData): SummaryExperiment[] {
  return data.evidence.filter(item => item.id.startsWith('experiment:')).map(item => item.data as SummaryExperiment)
}
export function experimentLabel(data: SummaryData, id: number): string {
  return summaryExperiments(data).find(item => item.id === id)?.experiment_no ?? `#${id}`
}
export function factValues(fact: SummaryFact, data: SummaryData): string {
  return data.experiment_ids.map(id => `${experimentLabel(data, id)}：${fact.values[id] ?? '缺失'}`).join('；')
}
export function summaryToText(summary: AISummary, stale: boolean): string {
  const lines = [
    'AI 实验总结（AI 建议，需人工核对）', `状态：${stale || summary.stale ? '已过期或尚未确认最新' : '对应下述数据快照'}`,
    `快照：${summary.fetched_at}`, `生成：${summary.generated_at}`, `模型：${summary.model}`,
    `实验：${summaryExperiments(summary.data).map(item => `${item.experiment_no} (${item.model_name}${item.has_result ? '' : '，无结果'})`).join('、')}`,
    `基准：${summary.data.baseline_experiment_id === null ? '未选择' : experimentLabel(summary.data, summary.data.baseline_experiment_id)}`,
    `主指标：${summary.data.primary_metric ?? '未选择；按指标分别总结'}`, '', '确定性事实：',
  ]
  for (const fact of summary.facts) {
    lines.push(`${fact.name} [${fact.id}] ${fact.unit}（${fact.direction === 'max' ? '越大越好' : '越小越好'}）：${factValues(fact, summary.data)}`)
    lines.push(`最佳：${fact.best.experiment_ids.map(id => experimentLabel(summary.data, id)).join('、') || '无'}；值：${fact.best.value ?? '缺失'}`)
    if (fact.baseline) {
      for (const id of summary.data.experiment_ids) {
        const delta = fact.baseline.comparisons[id]
        if (delta) lines.push(`${experimentLabel(summary.data, id)} 相对基准：${delta.delta ?? '不可用'}；${delta.status}；${delta.reason ?? ''}`)
      }
    }
  }
  for (const section of summary.narrative.sections) {
    lines.push('', sectionLabels[section.key] ?? section.key)
    for (const item of section.items) lines.push(`[${kindLabels[item.kind]}] ${item.text}（证据：${item.evidence_ids.join('、')}）`)
  }
  lines.push('', ...summary.data.warnings)
  return lines.join('\n')
}
