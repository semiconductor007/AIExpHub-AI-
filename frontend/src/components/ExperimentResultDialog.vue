<script setup lang="ts">
import { computed, nextTick, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import type { BuiltinMetric, ExperimentResult, ResultMetric, ResultPayload } from '../api/results'
import { metricLabel } from '../api/metrics'
import type { MetricDefinition } from '../api/metrics'
import ResultJsonMapper from './ResultJsonMapper.vue'

export interface ExperimentResultDraft {
  experimentId: number
  editing: boolean
  payload: ResultPayload
}

const props = defineProps<{
  projectId: number
  metrics: MetricDefinition[]
  submitting?: boolean
}>()
const emit = defineEmits<{ save: [draft: ExperimentResultDraft]; reading: [value: boolean] }>()

const visible = ref(false)
const editing = ref(false)
const experimentId = ref<number | null>(null)
const activeResult = ref<ExperimentResult | null>(null)
const formRef = ref<FormInstance>()
const form = reactive<Record<ResultMetric, string>>({ accuracy: '', precision: '', recall: '', f1: '', loss: '' })
const formError = ref('')
const mappingBlocked = ref(false)
const mapperVersion = ref(0)
const fileLoading = ref(false)

const metrics = computed(() => props.metrics)

function metricValue(metric: MetricDefinition): number | null {
  return metric.builtin ? activeResult.value?.[metric.key as BuiltinMetric] ?? null : activeResult.value?.custom_metrics?.[metric.key] ?? null
}

function parseMetric(key: ResultMetric, text: string): number | null {
  if (text.trim() === '') return null
  const number = Number(text)
  if (!Number.isFinite(number)) throw new Error('请输入有限的数值')
  const definition = metrics.value.find(metric => metric.key === key)
  if (!definition) throw new Error('项目指标已变化，请重新打开结果表单')
  if ((definition.lower_bound !== null && number < definition.lower_bound)
      || (definition.upper_bound !== null && number > definition.upper_bound)) {
    throw new Error(`指标必须处于 [${definition.lower_bound ?? '不限'}, ${definition.upper_bound ?? '不限'}]`)
  }
  return number
}

function applyResultMapping(values: Record<string, number | null>, replace: boolean): void {
  const fields: Record<string, string> = {}
  for (const metric of metrics.value) {
    if (replace || Object.hasOwn(values, metric.key)) {
      const value = values[metric.key]
      fields[metric.key] = value === null || value === undefined ? '' : String(value)
    }
  }
  Object.assign(form, fields)
  formError.value = ''
  formRef.value?.clearValidate()
}

const rules = computed<FormRules<typeof form>>(() => Object.fromEntries(metrics.value.map(metric => [metric.key, [{
  trigger: 'blur', validator: (_rule: unknown, value: unknown, callback: (error?: Error) => void) => {
    try {
      if (typeof value !== 'string') throw new Error('请输入有限的数值')
      parseMetric(metric.key, value)
      callback()
    } catch (error: unknown) { callback(error instanceof Error ? error : new Error('指标校验失败')) }
  }, }]])))

async function open(targetId: number, result: ExperimentResult | null): Promise<void> {
  experimentId.value = targetId
  activeResult.value = result
  editing.value = result !== null
  for (const key of Object.keys(form)) delete form[key]
  for (const metric of metrics.value) {
    const value = metricValue(metric)
    form[metric.key] = value === null || value === undefined ? '' : String(value)
  }
  formError.value = ''
  mappingBlocked.value = false
  mapperVersion.value += 1
  visible.value = true
  await nextTick()
  formRef.value?.clearValidate()
}

function close(): void {
  if (!props.submitting) visible.value = false
}

async function submit(): Promise<void> {
  if (props.submitting || !formRef.value || experimentId.value === null || mappingBlocked.value) return
  formError.value = ''
  if (!await formRef.value.validate().catch(() => false)) return
  try {
    const values = Object.fromEntries(metrics.value.map(metric => [metric.key, parseMetric(metric.key, form[metric.key] ?? '')]))
    if (Object.values(values).every(value => value === null)) {
      formError.value = '实验结果至少需要一个有效指标，0 也是合法值。'
      return
    }
    emit('save', {
      experimentId: experimentId.value,
      editing: editing.value,
      payload: {
        accuracy: values.accuracy ?? null,
        precision: values.precision ?? null,
        recall: values.recall ?? null,
        f1: values.f1 ?? null,
        loss: values.loss ?? null,
        custom_metrics: Object.fromEntries(metrics.value.filter(metric => !metric.builtin).map(metric => [metric.key, values[metric.key] ?? null])),
      },
    })
  } catch (error: unknown) {
    ElMessage.error(error instanceof Error ? error.message : '实验结果校验失败')
  }
}

function updateReading(value: boolean): void {
  fileLoading.value = value
  emit('reading', value)
}

defineExpose({ open, close })
</script>

<template>
  <el-dialog v-model="visible" class="aiexphub-result-dialog" :title="editing ? '编辑实验结果' : '录入实验结果'" width="min(780px, 94vw)" top="4vh"
             :close-on-click-modal="!submitting" :close-on-press-escape="!submitting" :show-close="!submitting">
    <p class="hint">每项可留空，至少填写一项。系统指标保留原范围；自定义指标遵循项目配置的单位和上下限。</p>
    <ResultJsonMapper v-if="visible" :key="mapperVersion" :project-id="projectId" :metrics="metrics" :disabled="submitting"
                      @applied="applyResultMapping" @blocked="mappingBlocked = $event" @reading="updateReading" />
    <el-alert v-if="formError" :title="formError" type="error" :closable="false" show-icon />
    <el-form ref="formRef" class="result-metric-form" :model="form" :rules="rules" label-position="top" :disabled="submitting || fileLoading" @submit.prevent="submit">
      <el-form-item v-for="metric in metrics" :key="metric.key" :label="metricLabel(metric)" :prop="metric.key">
        <p class="metric-hint">{{ metric.key }} · {{ metric.direction === 'max' ? '越大越好' : '越小越好' }} · {{ metric.lower_bound ?? '不限' }} ～ {{ metric.upper_bound ?? '不限' }}</p>
        <el-input v-model="form[metric.key]" inputmode="decimal" :aria-label="metricLabel(metric)" placeholder="留空表示无此指标" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button :disabled="submitting || fileLoading" @click="close">取消</el-button>
      <el-button type="primary" :loading="submitting || fileLoading" :disabled="submitting || fileLoading || mappingBlocked" @click="submit">保存结果</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.hint { color: #6b7280; line-height: 1.7; }
.result-metric-form { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 16px; }
.metric-hint { margin: 0 0 4px; color: #6b7280; font-size: 12px; width: 100%; }
@media (max-width: 480px) {
  .result-metric-form { grid-template-columns: minmax(0, 1fr); }
}
</style>

<style>
.aiexphub-result-dialog .el-dialog__body { max-height: 70vh; overflow-y: auto; padding-right: 6px; }
</style>
