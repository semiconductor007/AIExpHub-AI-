import axios from 'axios'

const networkMessage = '无法连接后端服务，请确认服务已启动。'
const detailMessages: Record<string, string> = {
  'Project has existing batches': '该项目仍包含实验批次，请先删除所有批次后再删除项目。',
  'Experiment batch has existing experiments': '该批次仍包含实验记录，请先删除相关实验后再删除批次。',
  'Project not found': '实验项目不存在，请刷新项目列表。',
  'Experiment batch not found': '实验批次不存在，请刷新批次列表。',
  'Project write conflict': '项目保存失败，请刷新后重试。',
  'Experiment batch write conflict': '批次保存失败，请刷新后重试。',
  'Experiment number already exists': '实验编号已存在，请使用其他编号。',
  'Experiment write conflict': '实验保存失败，请刷新后重试。',
  'Experiment not found': '实验记录不存在，请刷新列表。',
  'Experiment result already exists': '该实验结果已存在，请刷新后编辑。',
  'Experiment result not found': '该实验尚未录入结果。',
  'Experiment result write conflict': '实验结果保存失败，请刷新后重试。',
}

const fieldLabels: Record<string, string> = {
  name: '名称', description: '说明', experiment_no: '实验编号', model_name: '模型名称',
  parameters: '实验参数', accuracy: 'Accuracy', precision: 'Precision', recall: 'Recall', f1: 'F1', loss: 'Loss',
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

export function isApiErrorDetail(error: unknown, detail: string, status: number): boolean {
  return axios.isAxiosError<unknown>(error) && error.response?.status === status
    && isRecord(error.response.data) && error.response.data.detail === detail
}

export function getApiErrorMessage(error: unknown, fallback = '操作失败，请稍后重试。'): string {
  if (!axios.isAxiosError<unknown>(error)) return fallback
  const response = error.response
  // Vite returns an empty 500 response when its backend proxy cannot connect.
  if (!response || [502, 503, 504].includes(response.status)
      || (response.status === 500 && response.data === '')) return networkMessage
  const detail = isRecord(response.data) ? response.data.detail : undefined
  if (typeof detail === 'string') {
    const missingExperiment = /^Experiment not found: ([1-9]\d*)$/.exec(detail)
    if (missingExperiment) return `实验 ID ${missingExperiment[1]} 已不存在，请刷新候选列表并重新选择。`
    return detailMessages[detail] ?? detail
  }
  if (Array.isArray(detail)) {
    const messages = detail.filter(isRecord).map((item) => {
      if (Array.isArray(item.loc) && item.loc.includes('experiment_ids')) return '请选择至少两个不同的有效实验进行比较。'
      const field = Array.isArray(item.loc) ? item.loc.at(-1) : undefined
      const label = typeof field === 'string' ? fieldLabels[field] ?? '输入' : '输入'
      if (item.type === 'missing' || item.type === 'string_too_short') return `${label}不能为空。`
      if (item.type === 'string_type') return `${label}必须是文本。`
      if (field === 'parameters') return '实验参数必须是非空的合法 JSON 对象。'
      if (['accuracy', 'precision', 'recall', 'f1', 'loss'].includes(String(field))) {
        return field === 'loss' ? 'Loss 必须是大于等于 0 的有限数值。' : `${label}必须是 [0, 1] 内的有限数值。`
      }
      if (item.type === 'extra_forbidden') return '请求包含不允许修改的字段。'
      if (item.type === 'value_error' && ['name', 'experiment_no', 'model_name'].includes(String(field))) return `${label}不能为空或仅含空白字符。`
      if (item.type === 'value_error') return '输入校验失败，请检查必填字段及至少一项有效结果指标。'
      return `${label}校验失败，请检查输入。`
    })
    return messages.length ? messages.join('；') : '输入校验失败，请检查表单。'
  }
  return fallback
}
