import assert from 'node:assert/strict'
import test from 'node:test'
import { setVisibleSelection, keepExistingSelection } from '../src/utils/workspace-selection.ts'

test('batch filtering keeps hidden selections while checking and unchecking the visible rows', () => {
  assert.deepEqual(setVisibleSelection([4, 7], [4, 5, 6], true), [4, 7, 5, 6])
  assert.deepEqual(setVisibleSelection([4, 7, 5, 6], [4, 5, 6], false), [7])
})

test('refresh removes deleted experiments without losing remaining cross-batch choices', () => {
  assert.deepEqual(keepExistingSelection([4, 5, 7], [4, 6, 7, 8]), [4, 7])
})
