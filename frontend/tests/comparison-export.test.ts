import assert from 'node:assert/strict'
import test from 'node:test'
import { buildComparisonCsv, createExportSnapshot, csvCell, exportFilename, runComparisonExport } from '../src/utils/comparison-export.ts'
import { chartExportLayout, wrapChartLabel } from '../src/utils/chart-export-layout.ts'
import type { ExperimentCompareResponse } from '../src/api/compare.ts'

function fixture(): ExperimentCompareResponse {
  return {
    experiments: [
      { id: 1, experiment_no: 'EXP-001', model_name: '中文模型,"A"\n第二行', project_id: 10, batch_id: 20, result: { accuracy: 0, precision: 0.9, recall: null, f1: null, loss: 0.12345678901234568 } },
      { id: 2, experiment_no: '=USER-NUMBER', model_name: '模型 B', project_id: 10, batch_id: 20, result: { accuracy: 0.8, precision: 0.9, recall: null, f1: null, loss: 0 } },
      { id: 3, experiment_no: 'EXP-003', model_name: '模型 C', project_id: 11, batch_id: 21, result: null },
    ],
    best_by_metric: {
      accuracy: { direction: 'max', value: 0.8, experiment_ids: [2] }, precision: { direction: 'max', value: 0.9, experiment_ids: [1, 2] },
      recall: { direction: 'max', value: null, experiment_ids: [] }, f1: { direction: 'max', value: null, experiment_ids: [] },
      loss: { direction: 'min', value: 0, experiment_ids: [2] },
    },
    custom_metrics: [
      { definition: { id: 1, project_id: 10, key: 'latency', name: '延迟', unit: 'ms', direction: 'min', lower_bound: 0, upper_bound: null, builtin: false }, project_name: '项目 A', values: { 1: 10, 2: 5, 3: null }, best: { direction: 'min', value: 5, experiment_ids: [2] } },
      { definition: { id: 2, project_id: 11, key: 'latency', name: '延迟', unit: 's', direction: 'min', lower_bound: 0, upper_bound: null, builtin: false }, project_name: '项目 B', values: { 1: null, 2: null, 3: null }, best: { direction: 'min', value: null, experiment_ids: [] } },
    ],
  }
}

function snapshot() {
  return createExportSnapshot(fixture(), [{ id: 1, project_id: 10, project_name: '项目 A', batch_id: 20, batch_name: '批次甲' }], 0, 1000)
}

// Parse quoted fields and embedded newlines rather than splitting on commas or line breaks.
function parseCsv(csv: string): string[][] {
  const rows: string[][] = []
  let row: string[] = [], value = '', quoted = false
  const text = csv.replace(/^\uFEFF/, '')
  for (let index = 0; index < text.length; index++) {
    const character = text[index]
    if (character === '"') {
      if (quoted && text[index + 1] === '"') { value += '"'; index++ } else quoted = !quoted
    } else if (!quoted && (character === ',' || character === '\r')) {
      row.push(value); value = ''
      if (character === '\r') { rows.push(row); row = []; assert.equal(text[++index], '\n') }
    } else value += character
  }
  assert.equal(quoted, false)
  return rows
}

test('CSV is UTF-8 BOM / CRLF and preserves Chinese, quotes, embedded newlines and experiment order', () => {
  const csv = buildComparisonCsv(snapshot())
  assert.equal(csv.charCodeAt(0), 0xfeff)
  const rows = parseCsv(csv)
  assert.equal(rows.length, 4)
  assert.ok(rows.every(row => row.length === rows[0]!.length))
  assert.deepEqual(rows.slice(1).map(row => row[0]), ['1', '2', '3'])
  assert.equal(rows[1]![2], '中文模型,"A"\n第二行')
  assert.equal(rows[1]![4], '项目 A')
  assert.equal(rows[2]![4], 'Project #10')
  assert.equal(rows[1]![8], '1970-01-01T00:00:00.000Z')
  assert.equal(rows[1]![9], '1970-01-01T00:00:01.000Z')
})

test('zero, full numeric precision, missing metrics and no Result remain distinct', () => {
  const rows = parseCsv(buildComparisonCsv(snapshot()))
  const column = (part: string) => rows[0]!.findIndex(value => value.includes(part))
  assert.equal(rows[1]![column('Accuracy [accuracy] ↑ 越大越好 / 原始值')], '0')
  assert.equal(rows[1]![column('Loss [loss] ↓ 越小越好 / 原始值')], '0.12345678901234568')
  assert.equal(rows[1]![column('Recall [recall] ↑ 越大越好 / 原始值')], '')
  assert.equal(rows[1]![column('Recall [recall] ↑ 越大越好 / 指标状态')], '缺失指标')
  assert.equal(rows[3]![7], '未录入结果')
  assert.equal(rows[3]![column('Accuracy [accuracy] ↑ 越大越好 / 指标状态')], '未录入结果')
})

test('best flags use API ranking including ties; all-null metrics have no fabricated best', () => {
  const rows = parseCsv(buildComparisonCsv(snapshot()))
  const precision = rows[0]!.findIndex(value => value.includes('Precision') && value.endsWith('是否最佳'))
  const recall = rows[0]!.findIndex(value => value.includes('Recall') && value.endsWith('是否最佳'))
  assert.deepEqual(rows.slice(1).map(row => row[precision]), ['是', '是', ''])
  assert.deepEqual(rows.slice(1).map(row => row[recall]), ['', '', ''])
})

test('same-key custom metrics keep project, unit and direction; foreign rows are inapplicable', () => {
  const rows = parseCsv(buildComparisonCsv(snapshot()))
  assert.ok(rows[0]!.some(value => value.includes('项目 #10 项目 A / 延迟 [latency] (ms) ↓')))
  assert.ok(rows[0]!.some(value => value.includes('项目 #11 项目 B / 延迟 [latency] (s) ↓')))
  const value = rows[0]!.findIndex(header => header.includes('项目 #10') && header.endsWith('原始值'))
  assert.equal(rows[1]![value], '10')
  assert.equal(rows[3]![value], '')
  assert.equal(rows[3]![value + 1], '不适用（其他项目）')
  assert.equal(rows[3]![value + 2], '')
})

test('baseline columns are optional and preserve tiny / negative deltas, statuses and reasons', () => {
  const s = snapshot()
  assert.ok(!parseCsv(buildComparisonCsv(s))[0]!.includes('基准实验 ID'))
  s.result.baseline_comparison = { baseline_experiment_id: 1, metrics: [
    { key: 'loss', project_id: null, name: 'Loss', unit: '', direction: 'min', baseline_value: 0.12345678901234568, comparisons: {
      1: { delta: 0, status: 'unchanged', reason: null }, 2: { delta: -0.12345678901234568, status: 'improved', reason: null }, 3: { delta: null, status: 'unavailable', reason: 'experiment_result_missing' },
    } },
    { key: 'accuracy', project_id: null, name: 'Accuracy', unit: '', direction: 'max', baseline_value: 0, comparisons: { 2: { delta: 1e-15, status: 'improved', reason: null } } },
  ] }
  const rows = parseCsv(buildComparisonCsv(s))
  assert.equal(rows[1]![rows[0]!.indexOf('基准实验编号')], 'EXP-001')
  assert.equal(rows[1]![rows[0]!.indexOf('是否基准')], '是')
  const loss = rows[0]!.findIndex(value => value.includes('Loss') && value.endsWith('绝对差值'))
  assert.equal(rows[1]![loss], '0')
  assert.equal(rows[2]![loss], '-0.12345678901234568')
  assert.equal(rows[2]![loss + 1], '改善')
  assert.equal(rows[3]![loss], '')
  assert.equal(rows[3]![loss + 2], '实验未录入结果')
  const accuracy = rows[0]!.findIndex(value => value.includes('Accuracy') && value.endsWith('绝对差值'))
  assert.equal(rows[2]![accuracy], '1e-15')
})

test('formula-like text is escaped without turning real negative numeric deltas into text', () => {
  for (const text of ['=SUM(1,2)', '+cmd', '-text', '@text', '  =1', '\tname', '\nname']) assert.ok(csvCell(text).startsWith('"\''))
  assert.equal(csvCell(-0.25), '-0.25')
  assert.equal(csvCell(0), '0')
  assert.equal(csvCell('普通文本'), '"普通文本"')
  assert.equal(csvCell(null), '""')
  for (const value of [NaN, Infinity, -Infinity]) assert.throws(() => csvCell(value), /非有限/)
})

test('snapshot is detached from subsequent response and metadata changes', () => {
  const result = fixture()
  const metadata = [{ id: 1, project_id: 10, project_name: '旧项目', batch_id: 20, batch_name: '旧批次' }]
  const frozen = createExportSnapshot(result, metadata, 0, 1000)
  result.experiments[0]!.result!.accuracy = 1
  result.best_by_metric.precision.experiment_ids.length = 0
  metadata[0]!.project_name = '新项目'
  assert.equal(frozen.result.experiments[0]!.result!.accuracy, 0)
  assert.deepEqual(frozen.result.best_by_metric.precision.experiment_ids, [1, 2])
  assert.equal(frozen.metadata[0]!.project_name, '旧项目')
})

test('export refreshes once and delivers only the refreshed snapshot', async () => {
  let refreshed = 0, delivered = ''
  const fresh = snapshot()
  fresh.result.experiments[0]!.result!.accuracy = 0.95
  const success = await runComparisonExport({ refresh: async () => { refreshed++; return fresh }, isCurrent: () => true,
    generate: data => data.result.experiments[0]!.result!.accuracy,
    deliver: (value, data) => { delivered = `${value}/${data.fetchedAt}` },
  })
  assert.equal(success, true)
  assert.equal(refreshed, 1)
  assert.equal(delivered, '0.95/1970-01-01T00:00:00.000Z')
})

test('failed refresh never generates or downloads a stale file', async () => {
  const forbidden = () => { throw new Error('must not generate or download') }
  assert.equal(await runComparisonExport({ refresh: async () => null, isCurrent: () => true, generate: forbidden, deliver: forbidden }), false)
  await assert.rejects(runComparisonExport({ refresh: async () => { throw new Error('offline') }, isCurrent: () => true, generate: forbidden, deliver: forbidden }), /offline/)
})

test('selection deletion or route disposal during async generation prevents download', async () => {
  let current = true, generated = false
  await assert.rejects(runComparisonExport({ refresh: async () => snapshot(), isCurrent: () => current,
    generate: async () => { generated = true; await Promise.resolve(); current = false; return 'png' },
    deliver: () => assert.fail('outdated file downloaded'),
  }), /已取消/)
  assert.equal(generated, true)
  await assert.rejects(runComparisonExport({ refresh: async () => snapshot(), isCurrent: () => false,
    generate: () => assert.fail('cancelled export generated'), deliver: () => assert.fail('cancelled export downloaded'),
  }), /已取消/)
})

test('image generation errors do not trigger a download', async () => {
  await assert.rejects(runComparisonExport({ refresh: async () => snapshot(), isCurrent: () => true,
    generate: () => { throw new Error('image missing') }, deliver: () => assert.fail('failed image downloaded'),
  }), /image missing/)
})

test('filenames are safe for Windows and carry unambiguous UTC timestamp and extension', () => {
  assert.equal(exportFilename('project-1/a:b', '2026-10-27T04:05:06.123Z', 'png'), 'AIExpHub_project-1_a_b_20261027T040506Z.png')
})

test('image labels wrap without truncating Unicode; layout grows and bounds canvas memory', () => {
  const label = '中文实验编号-🚀-ABCDEFGHIJKLMNOPQRSTUVWXYZ'
  assert.equal(wrapChartLabel(label).replaceAll('\n', ''), label)
  assert.ok(chartExportLayout([label]).bottom > chartExportLayout(['EXP-1']).bottom)
  assert.ok(chartExportLayout(Array(8).fill('EXP-1')).width > chartExportLayout(['EXP-1']).width)
  assert.throws(() => chartExportLayout(Array(1000).fill('EXP-1')), /尺寸限制/)
})
