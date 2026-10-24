import assert from 'node:assert/strict'
import test from 'node:test'
import { affectsComparison, publishComparisonChange, readComparisonChange, subscribeComparisonChanges } from '../src/utils/comparison-changes.ts'
import { createComparisonRefresh } from '../src/utils/comparison-refresh.ts'

test('change messages accept only versioned positive resource identities', () => {
  for (const change of [{ kind: 'experiment', id: 2 }, { kind: 'experiment', id: 2, deleted: true }, { kind: 'project-metrics', id: 3 }]) {
    assert.deepEqual(readComparisonChange({ version: 1, change }), change)
  }
  for (const value of [null, {}, { version: 2, change: { kind: 'experiment', id: 2 } },
    ...[0, -1, 1.5, '2', true, Infinity].map(id => ({ version: 1, change: { kind: 'experiment', id } })),
    { version: 1, change: { kind: 'unknown', id: 2 } }, { version: 1, change: { kind: 'experiment', id: 2, deleted: 'yes' } }]) {
    assert.equal(readComparisonChange(value), null)
  }
})

test('only selected experiments and their project definitions cause a refresh', () => {
  const selected = [{ id: 1, project_id: 3 }, { id: 2, project_id: 4 }]
  assert.equal(affectsComparison({ kind: 'experiment', id: 2 }, selected), true)
  assert.equal(affectsComparison({ kind: 'experiment', id: 99 }, selected), false)
  assert.equal(affectsComparison({ kind: 'project-metrics', id: 3 }, selected), true)
  assert.equal(affectsComparison({ kind: 'project-metrics', id: 99 }, selected), false)
})

function harness() {
  let enabled = true
  let visible = true
  let busy = false
  let calls = 0
  let next = 0
  const timers = new Map<number, () => void>()
  const refresh = createComparisonRefresh({
    enabled: () => enabled, visible: () => visible, busy: () => busy,
    refresh: async () => { calls += 1; busy = true },
    setTimer: callback => { timers.set(++next, callback); return next },
    clearTimer: handle => { timers.delete(handle as number) },
  })
  return { refresh, timers, get calls() { return calls },
    enable: (value: boolean) => { enabled = value }, show: (value: boolean) => { visible = value },
    busy: (value: boolean) => { busy = value },
    tick() { for (const [id, callback] of [...timers]) { timers.delete(id); callback() } },
  }
}

test('notifications and paired focus/visibility events debounce into one request', () => {
  const h = harness()
  h.refresh.request(); h.refresh.request(); h.refresh.request()
  assert.equal(h.timers.size, 1)
  h.tick()
  assert.equal(h.calls, 1)
  assert.equal(h.refresh.hasPending(), false)
})

test('no comparison starts until the user has compared, and hidden tabs wait for visibility', () => {
  const h = harness()
  h.enable(false); h.refresh.request(); h.tick()
  assert.equal(h.calls, 0)
  h.enable(true); h.show(false); h.refresh.request(); h.tick()
  assert.equal(h.calls, 0)
  assert.equal(h.refresh.hasPending(), true)
  h.show(true); h.refresh.request(); h.tick()
  assert.equal(h.calls, 1)
})

test('changes during a manual or automatic request queue exactly one follow-up', () => {
  const h = harness()
  h.busy(true); h.refresh.request(); h.refresh.request(); h.tick()
  assert.equal(h.calls, 0)
  assert.equal(h.refresh.hasPending(), true)
  h.busy(false); h.refresh.settle(); h.tick()
  assert.equal(h.calls, 1)
  h.refresh.request(); h.refresh.request()
  h.busy(false); h.refresh.settle(); h.tick()
  assert.equal(h.calls, 2)
})

test('hiding or disabling between scheduling and execution suppresses the request', () => {
  const h = harness()
  h.refresh.request(); h.show(false); h.tick()
  assert.equal(h.calls, 0)
  h.show(true); h.refresh.request(); h.enable(false); h.tick()
  assert.equal(h.calls, 0)
  assert.equal(h.refresh.hasPending(), false)
})

test('manual refresh/selection reset clears queued requests; unmount disposes the scheduler', () => {
  const h = harness()
  h.refresh.request(); h.refresh.clear(); h.tick()
  assert.equal(h.calls, 0)
  h.refresh.request(); h.refresh.dispose(); h.tick()
  h.refresh.request(); h.refresh.settle(); h.tick()
  assert.equal(h.calls, 0)
  assert.equal(h.refresh.hasPending(), false)
})

test('an automatic failure does not start a polling or retry loop', async () => {
  let callback: (() => void) | undefined
  let calls = 0
  const refresh = createComparisonRefresh({ enabled: () => true, visible: () => true, busy: () => false,
    setTimer: cb => { callback = cb; return 1 }, clearTimer: () => { callback = undefined },
    refresh: async () => { calls += 1; throw new Error('offline') },
  })
  refresh.request(); callback!()
  await Promise.resolve()
  refresh.settle()
  assert.equal(calls, 1)
  assert.equal(refresh.hasPending(), false)
})

test('browser notification fallback and cleanup work without exposing values', () => {
  const originalWindow = Object.getOwnPropertyDescriptor(globalThis, 'window')
  const originalChannel = Object.getOwnPropertyDescriptor(globalThis, 'BroadcastChannel')
  const target = new EventTarget()
  const stored: string[] = []
  Object.defineProperty(globalThis, 'window', { configurable: true, value: Object.assign(target, { localStorage: { setItem: (_key: string, value: string) => stored.push(value) } }) })
  Object.defineProperty(globalThis, 'BroadcastChannel', { configurable: true, value: class { constructor() { throw new Error('unsupported') } } })
  try {
    const changes: unknown[] = []
    const unsubscribe = subscribeComparisonChanges(change => changes.push(change))
    publishComparisonChange({ kind: 'experiment', id: 9 })
    assert.deepEqual(changes, [{ kind: 'experiment', id: 9 }])
    assert.equal(stored.length, 1)
    assert.deepEqual(Object.keys(JSON.parse(stored[0]!).change).sort(), ['id', 'kind'])
    const storage = new Event('storage')
    Object.assign(storage, { key: 'aiexphub-comparison-changes-v1:latest', newValue: JSON.stringify({ version: 1, change: { kind: 'experiment', id: 10 } }) })
    target.dispatchEvent(storage)
    assert.equal(changes.length, 2)
    Object.assign(target, { localStorage: { setItem: () => { throw new Error('storage blocked') } } })
    assert.doesNotThrow(() => publishComparisonChange({ kind: 'experiment', id: 12 }))
    assert.deepEqual(changes.at(-1), { kind: 'experiment', id: 12 })
    unsubscribe()
    publishComparisonChange({ kind: 'experiment', id: 11 })
    target.dispatchEvent(storage)
    assert.equal(changes.length, 3)
  } finally {
    if (originalWindow) Object.defineProperty(globalThis, 'window', originalWindow)
    else Reflect.deleteProperty(globalThis, 'window')
    Object.defineProperty(globalThis, 'BroadcastChannel', originalChannel!)
  }
})
