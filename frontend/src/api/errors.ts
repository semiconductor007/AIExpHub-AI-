import axios from 'axios'

const networkMessage = '无法连接后端服务，请确认服务已启动。'
const detailMessages: Record<string, string> = {
  'Project has existing batches': '该项目仍包含实验批次，请先删除所有批次后再删除项目。',
  'Experiment batch has existing experiments': '该批次仍包含实验记录，请先删除相关实验后再删除批次。',
  'Project not found': '实验项目不存在，请刷新项目列表。',
  'Experiment batch not found': '实验批次不存在，请刷新批次列表。',
  'Project write conflict': '项目保存失败，请刷新后重试。',
  'Experiment batch write conflict': '批次保存失败，请刷新后重试。',
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

export function getApiErrorMessage(error: unknown, fallback = '操作失败，请稍后重试。'): string {
  if (!axios.isAxiosError<unknown>(error)) return fallback
  const response = error.response
  // Vite returns an empty 500 response when its backend proxy cannot connect.
  if (!response || [502, 503, 504].includes(response.status)
      || (response.status === 500 && response.data === '')) return networkMessage
  const detail = isRecord(response.data) ? response.data.detail : undefined
  if (typeof detail === 'string') return detailMessages[detail] ?? detail
  if (Array.isArray(detail)) {
    const messages = detail.filter(isRecord).map((item) => {
      const field = Array.isArray(item.loc) ? item.loc.at(-1) : undefined
      const label = field === 'name' ? '名称' : field === 'description' ? '说明' : '输入'
      if (item.type === 'missing' || item.type === 'string_too_short') return `${label}不能为空。`
      if (item.type === 'string_type') return `${label}必须是文本。`
      return typeof item.msg === 'string' ? `${label}：${item.msg}` : `${label}校验失败。`
    })
    return messages.length ? messages.join('；') : '输入校验失败，请检查表单。'
  }
  return fallback
}
