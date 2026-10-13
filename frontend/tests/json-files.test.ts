import assert from 'node:assert/strict'
import test from 'node:test'
import { readJsonFile, MAX_JSON_BYTES, parseJsonText } from '../src/utils/json-files.ts'

test('UTF-8 BOM and uppercase extension are accepted without changing values', async () => {
  const value = await readJsonFile(new File(['\uFEFF{"latency_ms":0,"accuracy":null}'], 'RESULT.JSON'))
  assert.deepEqual(JSON.parse(value), { latency_ms: 0, accuracy: null })
})

test('invalid JSON, wrong extension and oversized files are rejected', async () => {
  await assert.rejects(readJsonFile(new File(['{bad}'], 'bad.json')), SyntaxError)
  await assert.rejects(readJsonFile(new File(['{}'], 'bad.txt')), /json/)
  await assert.rejects(readJsonFile(new File([' '.repeat(MAX_JSON_BYTES + 1)], 'big.json')), /1 MiB/)
})

test('file contents include bulk metadata, custom metrics and null unchanged', async () => {
  const document = { project_id: 1, experiments: [{ experiment_no: 'test', parameters: { seed: 42 }, result: { score: 0, loss: null } }] }
  assert.deepEqual(JSON.parse(await readJsonFile(new File([JSON.stringify(document)], 'batch.json'))), document)
})

test('overflow numbers cannot silently become null during HTTP serialization', async () => {
  assert.throws(() => parseJsonText('{"experiments":[{"parameters":{"seed":1e400}}]}'), /有限数值/)
  await assert.rejects(readJsonFile(new File(['{"accuracy":0.8,"loss":1e400}'], 'overflow.json')), /有限数值/)
})
