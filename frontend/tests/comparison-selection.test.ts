import assert from 'node:assert/strict'
import test from 'node:test'
import { comparisonIds, comparisonQuery } from '../src/utils/comparison-selection.ts'

test('comparison links preserve order, remove duplicates and survive a refresh', () => {
  const query = comparisonQuery([4, 7, 4, 9], 7)
  assert.deepEqual(query, { ids: '4,7,9', baseline: '7' })
  assert.deepEqual(comparisonIds(query.ids), [4, 7, 9])
  assert.deepEqual(comparisonQuery([], 7), {})
  assert.deepEqual(comparisonQuery([4, 7], 9), { ids: '4,7' })
})

test('malformed links cannot silently select a different experiment', () => {
  for (const value of ['0', '-1', '1.5', '4,,7', '4,bad', '9007199254740992', ['4', '7']]) {
    assert.throws(() => comparisonIds(value))
  }
  assert.deepEqual(comparisonIds(undefined), [])
})
