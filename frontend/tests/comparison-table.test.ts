import assert from 'node:assert/strict'
import test from 'node:test'
import type { ExperimentCompareResponse } from '../src/api/compare.ts'
import { comparisonExperimentPage, comparisonMetricRows, experimentColumnCapacity, filterComparisonMetrics } from '../src/utils/comparison-table.ts'
import { buildComparisonCsv, createExportSnapshot } from '../src/utils/comparison-export.ts'

function fixture(): ExperimentCompareResponse {
  return {
    experiments: [
      { id: 1, experiment_no: '实验一', model_name: 'A', project_id: 10, batch_id: 1, result: { accuracy: 0, precision: .9, recall: null, f1: null, loss: .12345678901234568 } },
      { id: 2, experiment_no: '实验二', model_name: 'B', project_id: 10, batch_id: 2, result: { accuracy: .8, precision: .9, recall: null, f1: null, loss: 0 } },
      { id: 3, experiment_no: '实验三', model_name: 'C', project_id: 20, batch_id: 3, result: null },
    ],
    best_by_metric: {
      accuracy: { direction: 'max', value: .8, experiment_ids: [2] }, precision: { direction: 'max', value: .9, experiment_ids: [1, 2] },
      recall: { direction: 'max', value: null, experiment_ids: [] }, f1: { direction: 'max', value: null, experiment_ids: [] },
      loss: { direction: 'min', value: 0, experiment_ids: [2] },
    },
    custom_metrics: [
      { definition: { id: 7, project_id: 10, key: 'latency', name: '延迟', unit: 'ms', direction: 'min', lower_bound: 0, upper_bound: null, builtin: false }, project_name: '中文项目', values: { 1: 8, 2: null, 3: null }, best: { direction: 'min', value: 8, experiment_ids: [1] } },
      { definition: { id: 8, project_id: 20, key: 'latency', name: '延迟', unit: 's', direction: 'min', lower_bound: 0, upper_bound: null, builtin: false }, project_name: '其他项目', values: { 1: null, 2: null, 3: null }, best: { direction: 'min', value: null, experiment_ids: [] } },
    ],
    baseline_comparison: { baseline_experiment_id: 1, metrics: [
      { key: 'accuracy', project_id: null, name: 'Accuracy', unit: '', direction: 'max', baseline_value: 0, comparisons: { 1: { delta: 0, status: 'unchanged', reason: null }, 2: { delta: .8, status: 'improved', reason: null } } },
      { key: 'latency', project_id: 10, name: '延迟', unit: 'ms', direction: 'min', baseline_value: 8, comparisons: { 3: { delta: null, status: 'unavailable', reason: 'experiment_project_mismatch' } } },
    ] },
  }
}

test('transposed rows preserve zero, precision, missing metrics, missing results and ties', () => {
  const rows = comparisonMetricRows(fixture())
  assert.equal(rows[0]!.cells[1]!.value, 0)
  assert.equal(rows.find(row => row.key === 'loss')!.cells[1]!.value, .12345678901234568)
  assert.deepEqual(rows[1]!.bestIds, [1, 2])
  assert.equal(rows[1]!.cells[1]!.best, true)
  assert.equal(rows[1]!.cells[2]!.best, true)
  assert.equal(rows[2]!.cells[1]!.status, 'missing')
  assert.equal(rows[2]!.hasData, false)
  assert.equal(rows[0]!.cells[3]!.status, 'no-result')
  assert.equal(rows[0]!.cells[3]!.best, false)
})

test('project metric identity, unit, scope and baseline deltas cannot mix across projects', () => {
  const rows = comparisonMetricRows(fixture())
  const first = rows.find(row => row.id === 'custom:10:7')!
  const second = rows.find(row => row.id === 'custom:20:8')!
  assert.equal(first.unit, 'ms'); assert.equal(second.unit, 's')
  assert.equal(first.cells[3]!.status, 'not-applicable')
  assert.equal(second.cells[1]!.status, 'not-applicable')
  assert.equal(second.cells[3]!.status, 'no-result')
  assert.equal(first.cells[3]!.delta!.reason, 'experiment_project_mismatch')
  assert.equal(rows[0]!.cells[2]!.delta!.delta, .8)
  assert.equal(first.cells[1]!.delta, undefined)
})

test('search and selection filter complete metric identities without changing the source or CSV', () => {
  const source = fixture(), before = JSON.stringify(source)
  const csv = buildComparisonCsv(createExportSnapshot(source, [], 0, 0))
  const rows = comparisonMetricRows(source)
  assert.deepEqual(filterComparisonMetrics(rows, [], 'LATENCY', false).map(row => row.id), ['custom:10:7', 'custom:20:8'])
  assert.deepEqual(filterComparisonMetrics(rows, [], '中文项目', true).map(row => row.id), ['custom:10:7'])
  assert.deepEqual(filterComparisonMetrics(rows, ['custom:10:7'], '延迟', false).map(row => row.id), ['custom:20:8'])
  assert.equal(filterComparisonMetrics(rows, [], 'ms', true).length, 1)
  assert.ok(filterComparisonMetrics(rows, [], '', true).every(row => row.hasData))
  assert.equal(filterComparisonMetrics(rows, rows.map(row => row.id), '', false).length, 0)
  assert.equal(JSON.stringify(source), before)
  assert.equal(buildComparisonCsv(createExportSnapshot(source, [], 0, 0)), csv)
})

test('pagination retains every experiment once and pins the baseline on every group', () => {
  const experiments = Array.from({ length: 9 }, (_, i) => ({ ...fixture().experiments[0]!, id: i + 1 }))
  const pages = [1, 2, 3].map(page => comparisonExperimentPage(experiments, 5, 4, page))
  assert.ok(pages.every(group => group.experiments[0]!.id === 5))
  assert.deepEqual(pages.flatMap(group => group.experiments.slice(1).map(item => item.id)), [1, 2, 3, 4, 6, 7, 8, 9])
  assert.deepEqual([pages[0]!.first, pages[0]!.last, pages[2]!.first, pages[2]!.last], [1, 3, 7, 8])
  assert.equal(comparisonExperimentPage(experiments, 5, 4, 99).page, 3)
  assert.equal(comparisonExperimentPage(experiments, 5, 4, -1).page, 1)
})

test('off-page best values never turn a visible runner-up into a winner', () => {
  const source = fixture()
  const first = comparisonExperimentPage(source.experiments, undefined, 1, 1)
  const accuracy = comparisonMetricRows(source)[0]!
  assert.equal(first.experiments[0]!.id, 1)
  assert.equal(accuracy.cells[first.experiments[0]!.id]!.best, false)
  assert.deepEqual(accuracy.bestIds, [2])
  assert.equal(comparisonExperimentPage(source.experiments, undefined, 1, 2).experiments[0]!.id, 2)
})

test('responsive capacity keeps at least a baseline and one peer on narrow screens', () => {
  assert.equal(experimentColumnCapacity(1100, false), 4)
  assert.equal(experimentColumnCapacity(800, false), 3)
  assert.equal(experimentColumnCapacity(310, false), 1)
  assert.equal(experimentColumnCapacity(310, true), 2)
  const group = comparisonExperimentPage(fixture().experiments, 3, 2, 2)
  assert.deepEqual(group.experiments.map(item => item.id), [3, 2])
  const missingBaseline = comparisonExperimentPage(fixture().experiments, 99, 2, 2)
  assert.deepEqual(missingBaseline.experiments.map(item => item.id), [3])
  assert.equal(missingBaseline.baselineId, undefined)
})
