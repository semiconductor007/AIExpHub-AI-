const formatter = new Intl.DateTimeFormat('zh-CN', {
  year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false,
})

export function formatDateTime(value: string): string {
  if (!value) return '-'
  // SQLite may omit the offset; backend timestamps represent UTC.
  const date = new Date(/(Z|[+-]\d{2}:\d{2})$/i.test(value) ? value : `${value}Z`)
  return Number.isNaN(date.getTime()) ? value : formatter.format(date)
}
