import assert from 'node:assert/strict'
import test from 'node:test'
import { formatSignedDelta } from '../src/utils/metric-delta.ts'

test('ordinary floating-point tails are formatted with explicit positive signs', () => {
  assert.equal(formatSignedDelta(0.83 - 0.8), '+0.03')
  assert.equal(formatSignedDelta(0.3 - 0.4), '-0.1')
  assert.equal(formatSignedDelta(0), '0')
  assert.equal(formatSignedDelta(-0), '0')
})

test('tiny real differences are never rounded to zero', () => {
  assert.equal(formatSignedDelta(5e-324), '+5e-324')
  assert.equal(formatSignedDelta(-1e-20), '-1e-20')
  assert.equal(formatSignedDelta(1e-20), '+1e-20')
})

test('negative values and large finite differences keep sign and scale', () => {
  assert.equal(formatSignedDelta(-12), '-12')
  assert.equal(formatSignedDelta(10), '+10')
  assert.equal(formatSignedDelta(1e308), '+1e+308')
})
