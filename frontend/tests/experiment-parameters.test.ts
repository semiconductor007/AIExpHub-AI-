import assert from 'node:assert/strict'
import test from 'node:test'
import { parameterRowsFromObject, parameterRowsToObject, parseParameterObject } from '../src/utils/experiment-parameters.ts'

test('parameter rows preserve primitive types and serialize back to an object', () => {
  const rows = parameterRowsFromObject({ learning_rate: 0.0001, batch_size: 32, optimizer: 'AdamW', enabled: true })
  const object = parameterRowsToObject(rows)
  assert.deepEqual(JSON.parse(JSON.stringify(object)), {
    learning_rate: 0.0001,
    batch_size: 32,
    optimizer: 'AdamW',
    enabled: true,
  })
})

test('complex values use JSON rows and remain intact', () => {
  const rows = parameterRowsFromObject({ scheduler: { type: 'cosine' }, layers: [2, 4, 8], empty: null })
  assert.equal(rows.every(row => row.type === 'json'), true)
  assert.deepEqual(JSON.parse(JSON.stringify(parameterRowsToObject(rows))), {
    scheduler: { type: 'cosine' },
    layers: [2, 4, 8],
    empty: null,
  })
})

test('duplicate names, missing values and invalid JSON are rejected', () => {
  assert.throws(() => parameterRowsToObject([
    { key: 'seed', type: 'number', value: '1' },
    { key: ' seed ', type: 'number', value: '2' },
  ]), /重复/)
  assert.throws(() => parameterRowsToObject([{ key: '', type: 'text', value: 'x' }]), /参数名不能为空/)
  assert.throws(() => parameterRowsToObject([{ key: 'seed', type: 'number', value: 'NaN' }]), /有限数字/)
  assert.throws(() => parameterRowsToObject([{ key: 'layers', type: 'json', value: '[1,' }]), /JSON 值无效/)
})

test('parameter JSON accepts objects and rejects empty or scalar roots', () => {
  assert.deepEqual(parseParameterObject('{"seed":42}'), { seed: 42 })
  assert.throws(() => parseParameterObject('{}'), /非空 JSON 对象/)
  assert.throws(() => parseParameterObject('[]'), /非空 JSON 对象/)
  assert.throws(() => parseParameterObject('42'), /非空 JSON 对象/)
  assert.deepEqual(parseParameterObject('{}', true), {})
})
