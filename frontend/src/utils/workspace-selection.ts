/** Filtering a list changes only the visible checkboxes, retaining other batches. */
export function setVisibleSelection(current: number[], visible: number[], checked: boolean): number[] {
  const next = new Set(current)
  for (const id of visible) { if (checked) next.add(id); else next.delete(id) }
  return [...next]
}

export function keepExistingSelection(current: number[], existing: number[]): number[] {
  const available = new Set(existing)
  return current.filter(id => available.has(id))
}
