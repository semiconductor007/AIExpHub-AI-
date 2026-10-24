import assert from 'node:assert/strict'
import test from 'node:test'
import { inspectMetricJson, validateMetricChoices } from '../src/utils/json-metrics.ts'
import { captureMappings, templateChoices } from '../src/utils/mapping-templates.ts'
import type { MappingTemplate } from '../src/utils/mapping-templates.ts'

const metrics = [
  { key: 'accuracy', id: null, builtin: true, name: 'Accuracy', lower_bound: 0, upper_bound: 1 },
  { key: 'loss', id: null, builtin: true, name: 'Loss', lower_bound: 0, upper_bound: null },
  { key: 'latency', id: 7, builtin: false, name: 'Latency', lower_bound: 0, upper_bound: 100 },
]
const mappings = [
  { metric_key: 'accuracy', metric_id: null, builtin: true, pointer: '/eval/acc' },
  { metric_key: 'latency', metric_id: 7, builtin: false, pointer: '/time' },
]
const template: MappingTemplate = { id: 1, project_id: 3, name: 'evaluation', mappings }

test('a reused template reads new values, including zero/null, and skips unmapped metrics', () => {
  for (const accuracy of [0, 0.7, 0.95]) {
    const discovery = inspectMetricJson(JSON.stringify({ eval: { acc: accuracy }, time: null, logs: ['done'], loss: 9 }), metrics)
    const matched = templateChoices(template, metrics, discovery)
    assert.deepEqual(matched.missing, [])
    assert.equal(matched.arrayBlocked.size, 0)
    const validation = validateMetricChoices(discovery, metrics, matched.choices)
    assert.equal(validation.canApply, true)
    assert.deepEqual(validation.values, { accuracy, latency: null })
    assert.equal(matched.choices.loss, '')
    assert.deepEqual(captureMappings(metrics, discovery, matched.choices), mappings)
  }
})

test('missing paths and nonnumeric or out of range values cannot apply', () => {
  for (const value of [{}, { eval: { acc: '0.8' }, time: 12 }, { eval: { acc: true }, time: 12 }, { eval: { acc: 0.8 }, time: 101 }]) {
    const discovery = inspectMetricJson(JSON.stringify(value), metrics)
    const matched = templateChoices(template, metrics, discovery)
    assert.equal(validateMetricChoices(discovery, metrics, matched.choices).canApply, false)
  }
})

test('deleted custom metric never reconnects by same key or reused ID', () => {
  const invalid = { ...template, mappings: [mappings[0]!, { ...mappings[1]!, metric_id: null }] }
  const discovery = inspectMetricJson('{"eval":{"acc":0.8},"time":12}', metrics)
  const matched = templateChoices(invalid, metrics, discovery)
  assert.deepEqual(matched.missing, ['latency'])
  assert.equal(matched.choices.latency, '')
  const replaced = templateChoices(template, metrics.map(metric => metric.key === 'latency' ? { ...metric, id: 99 } : metric), discovery)
  assert.deepEqual(replaced.missing, ['latency'])
})

test('same metric identity uses its current key and current bounds', () => {
  const current = metrics.map(metric => metric.id === 7 ? { ...metric, key: 'duration', upper_bound: 10 } : metric)
  const discovery = inspectMetricJson('{"eval":{"acc":0.8},"time":12}', current)
  const matched = templateChoices(template, current, discovery)
  assert.deepEqual(matched.missing, [])
  assert.equal(matched.choices.duration, '/time')
  assert.match(validateMetricChoices(discovery, current, matched.choices).errors.duration!, /范围/)
})

test('array paths work for a manual import but cannot be captured as templates', () => {
  const discovery = inspectMetricJson('{"history":[{"acc":0.8}]}', metrics)
  const choices = { accuracy: '/history/0/acc', loss: '', latency: '' }
  assert.equal(validateMetricChoices(discovery, metrics, choices).canApply, true)
  assert.throws(() => captureMappings(metrics, discovery, choices), /数组下标/)
})

test('a stored object path cannot silently traverse a new array with the same pointer', () => {
  const objectTemplate = { ...template, mappings: [{ ...mappings[0]!, pointer: '/history/0/acc' }] }
  const object = inspectMetricJson('{"history":{"0":{"acc":0.8}}}', metrics)
  assert.equal(templateChoices(objectTemplate, metrics, object).arrayBlocked.size, 0)
  const array = inspectMetricJson('{"history":[{"acc":0.9}]}', metrics)
  assert.deepEqual([...templateChoices(objectTemplate, metrics, array).arrayBlocked], ['accuracy'])
})

test('escaped and numeric object keys remain exact; all skipped choices cannot save', () => {
  const discovery = inspectMetricJson('{"a/b":{"~name":0.8}}', metrics)
  const choices = { accuracy: '/a~1b/~0name', loss: '', latency: '' }
  assert.equal(captureMappings(metrics, discovery, choices)[0]!.pointer, '/a~1b/~0name')
  assert.throws(() => captureMappings(metrics, discovery, { accuracy: '', loss: '', latency: '' }), /至少映射/)
  assert.throws(() => captureMappings(metrics, discovery, { ...choices, accuracy: '/missing' }), /路径/)
})
