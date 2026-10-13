<script setup lang="ts">
import { onBeforeUnmount, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createProjectMetric, deleteProjectMetric, getProjectMetrics, updateProjectMetric } from '../api/metrics'
import type { MetricDefinition, MetricDefinitionPayload } from '../api/metrics'
import { getApiErrorMessage } from '../api/errors'

const props = defineProps<{ projectId: number | null; projectName?: string }>()
const metrics = ref<MetricDefinition[]>([])
const loading = ref(false)
const saving = ref(false)
const removing = ref(false)
const error = ref('')
const dialog = ref(false)
const formError = ref('')
const editingId = ref<number | null>(null)
const targetProject = ref<number | null>(null)
const form = reactive({ key: '', name: '', unit: '', direction: 'max' as 'max' | 'min', lower: '', upper: '' })
let request = 0

async function load(): Promise<void> {
  const target = props.projectId
  const current = ++request
  metrics.value = []
  error.value = ''
  loading.value = target !== null
  if (target === null) return
  try {
    const response = await getProjectMetrics(target)
    if (current === request) metrics.value = response
  } catch (exception) {
    if (current === request) error.value = getApiErrorMessage(exception, '指标加载失败，请重试。')
  } finally { if (current === request) loading.value = false }
}

function open(metric?: MetricDefinition): void {
  if (props.projectId === null || saving.value || removing.value) return
  targetProject.value = props.projectId
  editingId.value = metric?.id ?? null
  Object.assign(form, { key: metric?.key ?? '', name: metric?.name ?? '', unit: metric?.unit ?? '', direction: metric?.direction ?? 'max',
    lower: metric?.lower_bound == null ? '' : String(metric.lower_bound), upper: metric?.upper_bound == null ? '' : String(metric.upper_bound) })
  formError.value = ''
  dialog.value = true
}

function bound(text: string): number | null {
  if (!text.trim()) return null
  const value = Number(text)
  if (!Number.isFinite(value)) throw new Error('上下限必须是有限数值，或留空表示不限。')
  return value
}

async function save(): Promise<void> {
  if (saving.value || targetProject.value === null) return
  formError.value = ''
  saving.value = true
  const target = targetProject.value
  try {
    const key = form.key.trim().toLowerCase()
    if (!/^[a-z][a-z0-9_]{0,63}$/.test(key)) throw new Error('指标键需以小写字母开头，仅含字母、数字或下划线，最多 64 字符。')
    if (!form.name.trim()) throw new Error('指标名称不能为空。')
    const payload: MetricDefinitionPayload = { key, name: form.name.trim(), unit: form.unit.trim(), direction: form.direction, lower_bound: bound(form.lower), upper_bound: bound(form.upper) }
    if (payload.lower_bound !== null && payload.upper_bound !== null && payload.lower_bound > payload.upper_bound) throw new Error('下限不能大于上限。')
    if (editingId.value === null) await createProjectMetric(target, payload)
    else await updateProjectMetric(target, editingId.value, payload)
    dialog.value = false
    ElMessage.success('项目指标已保存，该项目下所有实验均可使用。')
    if (props.projectId === target) await load()
  } catch (exception) { formError.value = exception instanceof Error && !('isAxiosError' in exception) ? exception.message : getApiErrorMessage(exception) }
  finally { saving.value = false }
}

async function remove(metric: MetricDefinition): Promise<void> {
  if (metric.id === null || metric.builtin || saving.value || removing.value) return
  removing.value = true
  try {
    await ElMessageBox.confirm(`确定删除指标“${metric.name}”吗？已有数值的指标会拒绝删除。`, '删除指标', { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' })
    await deleteProjectMetric(metric.project_id, metric.id)
    ElMessage.success('指标已删除')
    if (props.projectId === metric.project_id) await load()
  } catch (exception) { if (exception !== 'cancel' && exception !== 'close') ElMessage.error(getApiErrorMessage(exception)) }
  finally { removing.value = false }
}

watch(() => props.projectId, () => { if (!saving.value) dialog.value = false; void load() }, { immediate: true })
onBeforeUnmount(() => { request += 1 })
</script>

<template>
  <el-card class="management-card" shadow="never">
    <template #header><div class="card-header"><h2>{{ projectName ? `${projectName} / 共享评价指标` : '项目共享评价指标' }}</h2>
      <div class="card-actions"><el-button :disabled="projectId === null || saving || removing" :loading="loading" @click="load">刷新指标</el-button>
        <el-button type="primary" :disabled="projectId === null || loading || saving || removing" @click="open()">新增指标</el-button></div>
    </div></template>
    <el-empty v-if="projectId === null" description="请选择项目查看共享指标" />
    <template v-else>
      <p class="hint">本项目所有批次和实验共享这些定义，各实验独立填写数值。已有数值的指标仅能修改显示名称。</p>
      <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
      <el-table v-else :data="metrics" v-loading="loading" row-key="key" aria-label="项目共享指标列表">
        <el-table-column prop="key" label="JSON 指标键" min-width="140" />
        <el-table-column prop="name" label="名称" min-width="120" />
        <el-table-column label="单位" min-width="80"><template #default="{ row }">{{ row.unit || '-' }}</template></el-table-column>
        <el-table-column label="方向" min-width="120"><template #default="{ row }">{{ row.direction === 'max' ? '↑ 越大越好' : '↓ 越小越好' }}</template></el-table-column>
        <el-table-column label="范围" min-width="110"><template #default="{ row }">{{ row.lower_bound ?? '不限' }} ～ {{ row.upper_bound ?? '不限' }}</template></el-table-column>
        <el-table-column label="操作" width="140"><template #default="{ row }"><span v-if="row.builtin">系统指标</span><template v-else>
          <el-button link type="primary" :disabled="saving || removing" @click="open(row)">编辑</el-button>
          <el-button link type="danger" :disabled="saving || removing" @click="remove(row)">删除</el-button>
        </template></template></el-table-column>
      </el-table>
    </template>
  </el-card>
  <el-dialog v-model="dialog" :title="editingId === null ? '新增项目指标' : '编辑项目指标'" width="min(520px,92vw)" top="5vh" :close-on-click-modal="!saving" :close-on-press-escape="!saving" :show-close="!saving">
    <el-alert v-if="formError" :title="formError" type="error" :closable="false" show-icon />
    <el-form label-position="top" :disabled="saving" @submit.prevent="save">
      <el-form-item label="指标键（JSON 对应键）"><el-input v-model="form.key" aria-label="指标键" placeholder="例如 latency_ms" :disabled="editingId !== null" /></el-form-item>
      <el-form-item label="显示名称"><el-input v-model="form.name" aria-label="指标名称" placeholder="例如 平均推理耗时" /></el-form-item>
      <el-form-item label="单位（可选）"><el-input v-model="form.unit" aria-label="指标单位" placeholder="例如 ms" /></el-form-item>
      <el-form-item label="评价方向"><el-select v-model="form.direction" aria-label="评价方向"><el-option value="max" label="越大越好" /><el-option value="min" label="越小越好" /></el-select></el-form-item>
      <div class="bounds"><el-form-item label="下限（留空表示不限）"><el-input v-model="form.lower" aria-label="指标下限" inputmode="decimal" /></el-form-item>
        <el-form-item label="上限（留空表示不限）"><el-input v-model="form.upper" aria-label="指标上限" inputmode="decimal" /></el-form-item></div>
    </el-form>
    <template #footer><el-button :disabled="saving" @click="dialog = false">取消</el-button><el-button type="primary" :loading="saving" @click="save">保存指标</el-button></template>
  </el-dialog>
</template>

<style scoped>
.hint { color: #6b7280; line-height: 1.7; }
.bounds { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
</style>
