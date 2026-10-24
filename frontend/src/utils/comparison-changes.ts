/** Only resource identities cross tabs. Failed notifications never fail a saved write. */
export type ComparisonChange =
  | { kind: 'experiment'; id: number; deleted?: boolean }
  | { kind: 'project-metrics'; id: number }

const channelName = 'aiexphub-comparison-changes-v1'
const localEvent = `${channelName}:local`
const storageKey = `${channelName}:latest`

export function readComparisonChange(value: unknown): ComparisonChange | null {
  if (typeof value !== 'object' || value === null) return null
  const envelope = value as Record<string, unknown>
  if (envelope.version !== 1 || typeof envelope.change !== 'object' || envelope.change === null) return null
  const change = envelope.change as Record<string, unknown>
  if (typeof change.id !== 'number' || !Number.isSafeInteger(change.id) || change.id <= 0) return null
  if (change.kind === 'project-metrics') return { kind: change.kind, id: change.id }
  if (change.kind !== 'experiment' || (change.deleted !== undefined && typeof change.deleted !== 'boolean')) return null
  return { kind: change.kind, id: change.id, ...(change.deleted === undefined ? {} : { deleted: change.deleted }) }
}

export function affectsComparison(change: ComparisonChange, experiments: { id: number; project_id: number }[]): boolean {
  return experiments.some(item => change.kind === 'experiment' ? item.id === change.id : item.project_id === change.id)
}

export function publishComparisonChange(change: ComparisonChange): void {
  if (typeof window === 'undefined') return
  const envelope = { version: 1, change, nonce: `${Date.now()}-${Math.random()}` }
  try { window.dispatchEvent(new CustomEvent(localEvent, { detail: envelope })) } catch { /* Best effort. */ }
  try {
    const channel = new BroadcastChannel(channelName)
    try { channel.postMessage(envelope) } finally { channel.close() }
    return
  } catch { /* Browsers without BroadcastChannel can use the storage event. */ }
  try { window.localStorage.setItem(storageKey, JSON.stringify(envelope)) } catch { /* Focus refresh still works. */ }
}

export function subscribeComparisonChanges(listener: (change: ComparisonChange) => void): () => void {
  const receive = (value: unknown) => {
    const change = readComparisonChange(value)
    if (change) listener(change)
  }
  const local = (event: Event) => receive((event as CustomEvent<unknown>).detail)
  const storage = (event: StorageEvent) => {
    if (event.key !== storageKey || event.newValue === null) return
    try { receive(JSON.parse(event.newValue)) } catch { /* Ignore malformed unrelated input. */ }
  }
  let channel: BroadcastChannel | undefined
  window.addEventListener(localEvent, local)
  // Listen even when BroadcastChannel works: another tab may need its storage fallback.
  window.addEventListener('storage', storage)
  try {
    channel = new BroadcastChannel(channelName)
    channel.onmessage = event => receive(event.data)
  } catch { /* The storage listener and focus checks remain available. */ }
  return () => {
    window.removeEventListener(localEvent, local)
    window.removeEventListener('storage', storage)
    channel?.close()
  }
}
