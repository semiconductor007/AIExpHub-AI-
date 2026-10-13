import assert from 'node:assert/strict'
import test from 'node:test'
import { defaultMetricChoices, inspectMetricJson, jsonValueLabel, validateMetricChoices } from '../src/utils/json-metrics.ts'
import type { MetricRule } from '../src/utils/json-metrics.ts'

const metrics: MetricRule[] = [
  { key: 'accuracy', name: 'Accuracy', lower_bound: 0, upper_bound: 1 },
  { key: 'loss', name: 'Loss', lower_bound: 0, upper_bound: null },
  { key: 'latency_ms', name: '耗时', lower_bound: 0, upper_bound: 100 },
]

function inspect(value: unknown) {
  const discovery = inspectMetricJson(JSON.stringify(value), metrics)
  const choices = defaultMetricChoices(discovery, metrics)
  return { discovery, choices, validate: () => validateMetricChoices(discovery, metrics, choices) }
}

test('flat input preserves legacy detection, numeric zero and null', () => {
  const input = inspect({ accuracy: 0, loss: null })
  assert.equal(input.discovery.simple, true)
  assert.deepEqual(input.validate().values, { accuracy: 0, loss: null })
  assert.equal(input.validate().canApply, true)
  assert.equal(input.choices.latency_ms, '')
})

test('nested metrics coexist with unrelated config, strings and logs', () => {
  const input = inspect({ model: 'ResNet18', parameters: { seed: 42 }, logs: ['complete'], evaluation: { accuracy: 0.91, loss: 0.2 } })
  assert.equal(input.discovery.simple, false)
  assert.equal(input.choices.accuracy, '/evaluation/accuracy')
  assert.deepEqual(input.validate().values, { accuracy: 0.91, loss: 0.2 })
  const ignored = input.discovery.fields.filter(field => field.leaf && !input.validate().used.has(field.pointer))
  assert.deepEqual(ignored.map(field => field.path), ['$.model', '$.parameters.seed', '$.logs[0]'])
})

test('train and evaluation duplicates require an explicit choice', () => {
  const input = inspect({ train: { accuracy: 0.99 }, evaluation: { accuracy: 0.91, loss: 0.2 } })
  assert.equal(input.choices.accuracy, null)
  assert.equal(input.validate().canApply, false)
  assert.match(input.validate().errors.accuracy!, /多个候选/)
  input.choices.accuracy = '/evaluation/accuracy'
  assert.equal(input.validate().canApply, true)
  assert.equal(input.validate().values.accuracy, 0.91)
  input.choices.accuracy = ''
  assert.deepEqual(input.validate().values, { loss: 0.2 })
})

test('array records and history values are never silently reduced to latest', () => {
  const input = inspect([{ evaluation: { accuracy: 0.7 } }, { evaluation: { accuracy: 0.9 } }])
  assert.equal(input.choices.accuracy, null)
  assert.equal(input.validate().canApply, false)
  input.choices.accuracy = '/1/evaluation/accuracy'
  assert.equal(input.validate().values.accuracy, 0.9)
  assert.equal(input.discovery.fields[1]!.path, '$[1].evaluation.accuracy')
})

test('manual aliases map only after explicit selection', () => {
  const input = inspect({ test_acc: 0.8, duration: 12 })
  assert.equal(input.validate().canApply, false)
  assert.deepEqual(input.validate().values, {})
  input.choices.accuracy = '/test_acc'
  input.choices.latency_ms = '/duration'
  assert.deepEqual(input.validate().values, { accuracy: 0.8, latency_ms: 12 })
})

test('selected values must be finite numbers or null in the project range', () => {
  for (const value of ['0.8', true, [], {}, -0.1, 1.1]) {
    const input = inspect({ evaluation: { accuracy: value }, loss: 0.2 })
    assert.equal(input.validate().canApply, false)
    assert.ok(input.validate().errors.accuracy)
  }
  for (const value of [-1, 101]) {
    assert.equal(inspect({ latency_ms: value }).validate().canApply, false)
  }
  assert.equal(inspect({ latency_ms: 100 }).validate().canApply, true)
})

test('metric containers are complex documents and require explicit child mapping', () => {
  const input = inspect({ accuracy: { value: 0.8, unit: 'ratio' } })
  assert.equal(input.discovery.simple, false)
  assert.equal(input.validate().canApply, false)
  input.choices.accuracy = '/accuracy/value'
  assert.equal(input.validate().canApply, true)
  assert.deepEqual(input.validate().values, { accuracy: 0.8 })
})

test('known invalid values cannot be hidden by another valid metric', () => {
  const input = inspect({ accuracy: 'bad', loss: 0 })
  assert.equal(input.validate().canApply, false)
  input.choices.accuracy = '' // The user explicitly excludes the source field.
  assert.equal(input.validate().canApply, true)
  assert.deepEqual(input.validate().values, { loss: 0 })
})

test('selected overflow is rejected while unrelated overflow can be ignored', () => {
  const discovery = inspectMetricJson('{"memory":1e400,"evaluation":{"accuracy":0.8}}', metrics)
  const choices = defaultMetricChoices(discovery, metrics)
  assert.equal(validateMetricChoices(discovery, metrics, choices).canApply, true)
  choices.accuracy = '/memory'
  assert.equal(validateMetricChoices(discovery, metrics, choices).canApply, false)
})

test('all-null, unmatched and empty documents cannot apply an empty result', () => {
  for (const value of [{}, [], { accuracy: null }, { logs: ['done'], foo: 12 }]) {
    assert.equal(inspect(value).validate().canApply, false)
  }
})

test('special property names have unique escaped pointers and readable paths', () => {
  const input = inspect({ 'a/b': { 'a~b': 0.7 }, '评价': { 'test.acc': 0.8 } })
  input.choices.accuracy = '/a~1b/a~0b'
  assert.equal(input.validate().values.accuracy, 0.7)
  input.choices.accuracy = '/评价/test.acc'
  assert.equal(input.validate().values.accuracy, 0.8)
  assert.equal(input.discovery.fields[1]!.path, '$["评价"]["test.acc"]')
})

test('wrong pointer and case differences are not auto guesses', () => {
  const input = inspect({ Accuracy: 0.8 })
  assert.equal(input.validate().canApply, false)
  input.choices.accuracy = '/not-present'
  assert.match(input.validate().errors.accuracy!, /不存在/)
})

test('invalid syntax, scalar roots and resource limits fail explicitly', () => {
  assert.throws(() => inspectMetricJson('{bad}', metrics), SyntaxError)
  for (const value of [null, 12, 'abc', true]) assert.throws(() => inspectMetricJson(JSON.stringify(value), metrics), /对象或记录数组/)
  assert.throws(() => inspectMetricJson(' '.repeat(1024 * 1024 + 1), metrics), /1 MiB/)
  let deep: unknown = { accuracy: 0.8 }
  for (let i = 0; i < 101; i++) deep = { nested: deep }
  assert.throws(() => inspectMetricJson(JSON.stringify(deep), metrics), /嵌套过深/)
  assert.throws(() => inspectMetricJson(JSON.stringify({ logs: Array(20_001).fill('done') }), metrics), /字段过多/)
  assert.throws(() => inspectMetricJson(JSON.stringify(Array(100_001).fill({})), metrics), /结构过大/)
})

test('large irrelevant logs retain metrics located after the logs', () => {
  const input = inspect({ logs: Array(10_000).fill('completed'), evaluation: { accuracy: 0.9, latency_ms: 0 } })
  assert.equal(input.validate().canApply, true)
  assert.deepEqual(input.validate().values, { accuracy: 0.9, latency_ms: 0 })
})

test('inspection never mutates the source or invents metric values', () => {
  const source = { metadata: { loss_threshold: 0.1 }, result: { accuracy: 0.8 } }
  const original = JSON.stringify(source)
  const input = inspect(source)
  assert.equal(JSON.stringify(source), original)
  assert.equal('loss' in input.validate().values, false)
  assert.equal('latency_ms' in input.validate().values, false)
})

test('labels cap long strings and describe non-numeric types', () => {
  assert.match(jsonValueLabel('a'.repeat(100)), /…/)
  assert.equal(jsonValueLabel(Infinity), '非有限数值')
  assert.equal(jsonValueLabel({ accuracy: 0.8 }), '对象')
  assert.equal(jsonValueLabel([1, 2]), '数组（2 项）')
})
