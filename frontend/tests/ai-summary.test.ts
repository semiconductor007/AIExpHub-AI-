import assert from 'node:assert/strict'
import test from 'node:test'
import { factValues, summaryExperiments, summaryToText } from '../src/utils/ai-summary.ts'
import type { AISummary } from '../src/api/ai-summaries.ts'

function fixture(): AISummary {
  return {
    fingerprint: 'f'.repeat(64), fetched_at: '2026-10-27T03:00:00+00:00', generated_at: '2026-10-27T03:00:20+00:00', model: 'test-model', stale: false,
    data: { experiment_ids: [1, 2, 3], baseline_experiment_id: 1, primary_metric: null, warnings: ['评测条件仍需核对'], evidence: [
      ...[1, 2, 3].map(id => ({ id: `experiment:${id}`, experiment_ids: [id], metric_ids: [], data: { id, experiment_no: `实验-${id}`, model_name: '模型甲', project_id: 1, batch_id: 1, has_result: id !== 3, parameters: {} } })),
    ] },
    facts: [{ id: 'system:loss', key: 'loss', name: 'Loss', unit: '', direction: 'min', values: { 1: 0.3, 2: 0, 3: null }, best: { value: 0, experiment_ids: [2] }, baseline: { comparisons: { 2: { delta: -0.3, status: 'improved', reason: null }, 3: { delta: null, status: 'unavailable', reason: 'experiment_result_missing' } } } }],
    narrative: { sections: [{ key: 'limitations', items: [{ kind: 'hypothesis', text: '需要控制变量验证。', experiment_ids: [1, 2], metric_ids: ['system:loss'], evidence_ids: ['metric:system:loss'] }] }] },
  }
}

test('facts preserve real zero and distinguish missing values', () => {
  const data = fixture()
  assert.equal(factValues(data.facts[0]!, data.data), '实验-1：0.3；实验-2：0；实验-3：缺失')
  assert.equal(summaryExperiments(data.data).length, 3)
})
test('copied summary includes provenance, missing result, baseline, facts and evidence', () => {
  const text = summaryToText(fixture(), false)
  for (const expected of ['test-model', '2026-10-27T03:00:00', '实验-3 (模型甲，无结果)', '基准：实验-1', '最佳：实验-2；值：0', '-0.3', '不可用', 'metric:system:loss', '待验证推测', '评测条件仍需核对']) assert.ok(text.includes(expected), expected)
  assert.ok(!text.includes('已过期'))
})
test('copy cannot lose locally detected stale status', () => {
  assert.ok(summaryToText(fixture(), true).includes('已过期或尚未确认最新'))
})
test('copy cannot lose backend detected stale status', () => {
  assert.ok(summaryToText({ ...fixture(), stale: true }, false).includes('已过期或尚未确认最新'))
})
test('no baseline or main metric does not invent one', () => {
  const data = fixture()
  data.data.baseline_experiment_id = null
  const text = summaryToText(data, false)
  assert.ok(text.includes('基准：未选择'))
  assert.ok(text.includes('主指标：未选择；按指标分别总结'))
})
