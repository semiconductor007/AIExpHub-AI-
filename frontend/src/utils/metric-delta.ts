// Round for display without turning tiny, nonzero changes into zero.
export function formatSignedDelta(value: number): string {
  const formatted = Number(value.toPrecision(12)).toString()
  return value > 0 ? `+${formatted}` : formatted
}
