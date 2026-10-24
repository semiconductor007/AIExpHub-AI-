import assert from 'node:assert/strict'
import test from 'node:test'
import { copyExperimentDraft } from '../src/utils/experiment-copy.ts'

test('copy draft omits identity and result and editing nested parameters cannot change source', () => {
  const source = { id: 7, experiment_no: 'OLD', model_name: 'Model',
    parameters: { seed: 42, nested: { layers: [1, 2] } }, notes: 'baseline', result: { accuracy: 0.9 } }
  const original = structuredClone(source)
  const draft = copyExperimentDraft(source)
  assert.deepEqual(Object.keys(draft).sort(), ['experiment_no', 'model_name', 'notes', 'parameters'])
  assert.equal(draft.experiment_no, '')
  assert.equal(draft.model_name, 'Model')
  assert.equal(draft.notes, 'baseline')
  const edited = JSON.parse(draft.parameters)
  edited.nested.layers[0] = 99
  draft.parameters = JSON.stringify(edited)
  draft.notes = 'changed'
  assert.deepEqual(source, original)
})

test('optional notes become an empty editable field', () => {
  const draft = copyExperimentDraft({ model_name: 'M', parameters: { temperature: 0 }, notes: null })
  assert.equal(draft.notes, '')
  assert.deepEqual(JSON.parse(draft.parameters), { temperature: 0 })
})
