/** Debounce visible refreshes and retain one follow-up when a change arrives mid-request. */
export function createComparisonRefresh(options: {
  enabled: () => boolean
  visible: () => boolean
  busy: () => boolean
  refresh: () => Promise<void>
  setTimer?: (callback: () => void, delay: number) => unknown
  clearTimer?: (handle: unknown) => void
}) {
  const setTimer = options.setTimer ?? ((callback, delay) => setTimeout(callback, delay))
  const clearTimer = options.clearTimer ?? (handle => clearTimeout(handle as ReturnType<typeof setTimeout>))
  let timer: unknown
  let pending = false
  let disposed = false

  function cancelTimer() {
    if (timer !== undefined) clearTimer(timer)
    timer = undefined
  }
  function settle() {
    if (disposed || !pending || !options.enabled() || !options.visible() || options.busy()) return
    cancelTimer()
    timer = setTimer(() => {
      timer = undefined
      if (disposed || !options.enabled()) { pending = false; return }
      if (!options.visible() || options.busy()) return
      pending = false
      // The view owns errors; do not schedule endless retries after a failure.
      void options.refresh().catch(() => {})
    }, 250)
  }
  return {
    request() {
      if (disposed || !options.enabled()) return
      pending = true
      settle()
    },
    settle,
    hasPending: () => pending,
    clear() { pending = false; cancelTimer() },
    dispose() { disposed = true; pending = false; cancelTimer() },
  }
}
