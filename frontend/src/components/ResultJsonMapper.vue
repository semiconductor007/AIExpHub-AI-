<script setup lang="ts">
import { computed, onBeforeUnmount, ref, shallowRef, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { MetricDefinition } from '../api/metrics'
import { metricLabel } from '../api/metrics'
import { readJsonFile } from '../utils/json-files'
import { defaultMetricChoices, inspectMetricJson, jsonValueLabel, validateMetricChoices } from '../utils/json-metrics'
import type { MetricDiscovery } from '../utils/json-metrics'

const props = defineProps<{ metrics: MetricDefinition[]; disabled?: boolean }>()
const emit = defineEmits<{ applied: [values: Record<string, number | null>, replace: boolean]; blocked: [value: boolean]; reading: [value: boolean] }>()
const text = ref('')
const discovery = shallowRef<MetricDiscovery | null>(null)
const choices = ref<Record<string, string | null>>({})
const error = ref('')
const fileError = ref('')
const reading = ref(false)
const pending = ref(false)
let readRequest = 0
let active = true
const validation = computed(() => discovery.value ? validateMetricChoices(discovery.value, props.metrics, choices.value) : null)
const ignored = computed(() => discovery.value?.fields.filter(field => field.leaf && !validation.value?.used.has(field.pointer)) ?? [])
const options = computed(() => [
  { label: discovery.value?.simple ? '不映射（平铺模式清空该项）' : '不映射（保留当前输入）', value: '__skip__' },
  ...(discovery.value?.fields.map(field => ({ label: `${field.path} → ${jsonValueLabel(field.value)}`, value: field.pointer })) ?? []),
])
const blocked = computed(() => reading.value || !!fileError.value || !!error.value || (text.value.trim() !== '' && pending.value))
watch(blocked, value => emit('blocked', value), { immediate: true, flush: 'sync' })
watch(reading, value => emit('reading', value), { flush: 'sync' })

function apply(showMessage = true): void {
  if (props.disabled || reading.value || !discovery.value || !validation.value?.canApply) return
  emit('applied', validation.value.values, discovery.value.simple)
  pending.value = false
  if (showMessage) ElMessage.success('已按选定路径填入指标；可继续手动修正后保存。')
}

function inspect(): void {
  discovery.value = null
  error.value = ''
  fileError.value = ''
  pending.value = !!text.value.trim()
  if (!text.value.trim()) return
  try {
    discovery.value = inspectMetricJson(text.value, props.metrics)
    choices.value = defaultMetricChoices(discovery.value, props.metrics)
    if (discovery.value.simple && validation.value?.canApply && !reading.value) apply(false)
  } catch (exception) { error.value = exception instanceof SyntaxError ? '请输入合法 JSON，字段名需使用双引号。原输入未被覆盖。' : (exception as Error).message }
}
watch(text, inspect, { flush: 'sync' })
watch(() => props.metrics, inspect)

function select(key: string, pointer: unknown): void {
  choices.value[key] = typeof pointer === 'string' && pointer !== '__skip__' ? pointer : ''
  pending.value = true
}

async function chooseFile(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file || props.disabled || reading.value) return
  const request = ++readRequest
  reading.value = true
  fileError.value = ''
  try {
    const contents = await readJsonFile(file, false)
    if (request !== readRequest || !active) return
    text.value = contents
    inspect() // Re-selecting the same file must refresh its preview as well.
  } catch (exception) {
    if (request === readRequest && active) fileError.value = `${exception instanceof SyntaxError ? '文件不是合法 JSON，原输入未被覆盖。' : (exception as Error).message} 请换文件，或关闭此提示后继续录入。`
  } finally {
    if (active && request === readRequest) {
      reading.value = false
      if (discovery.value?.simple && validation.value?.canApply && !fileError.value) apply(false)
    }
    input.value = ''
  }
}
onBeforeUnmount(() => { active = false; readRequest += 1 })
</script>

<template>
  <section class="json-mapper" aria-label="JSON 指标识别与映射">
    <label class="heading">JSON 指标录入（可选）</label>
    <p class="hint">平铺指标 JSON 自动填入；复杂 JSON 先选择字段路径，再应用映射。只按项目指标键识别，不自动换算单位。</p>
    <label class="file-label">选择结果 JSON 文件（最多 1 MiB）<input type="file" accept=".json,application/json" aria-label="结果 JSON 文件" :disabled="disabled || reading" @change="chooseFile" /></label>
    <el-alert v-if="fileError" :title="fileError" type="error" show-icon @close="fileError = ''" />
    <el-input v-model="text" aria-label="结果 JSON" type="textarea" :rows="5" :disabled="disabled || reading" placeholder='{"evaluation":{"accuracy":0.91,"loss":0.2},"model":"ResNet18","logs":["训练完成"]}' />
    <div class="actions"><el-button :disabled="disabled || reading || !text" @click="text = ''">清空 JSON，继续手动录入</el-button></div>
    <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
    <template v-if="discovery && validation">
      <p class="hint" aria-live="polite">{{ discovery.simple && !pending ? '已自动填入，可核对下方指标。' : pending ? '映射待确认；应用前不会改变下方指标。' : '已应用映射；保存采用下方手动修正后的值。' }}</p>
      <details :open="!discovery.simple">
        <summary>指标路径映射</summary>
        <el-table :data="metrics" row-key="key" aria-label="指标路径映射列表" max-height="340">
          <el-table-column label="项目指标" min-width="150"><template #default="{ row }">{{ metricLabel(row) }}<p class="hint">{{ row.key }} · {{ row.lower_bound ?? '不限' }} ～ {{ row.upper_bound ?? '不限' }}</p></template></el-table-column>
          <el-table-column label="源字段（可搜索其他字段）" min-width="320"><template #default="{ row }">
            <el-select-v2 :model-value="choices[row.key] === '' ? '__skip__' : choices[row.key]" :options="options" filterable :disabled="disabled || reading" :aria-label="`${row.key} 来源字段`" placeholder="多个候选，请选择或不映射" @change="select(row.key, $event)" />
            <p v-if="(discovery.candidates.get(row.key)?.length ?? 0) > 1" class="hint">发现 {{ discovery.candidates.get(row.key)?.length }} 个同名候选，请选择实际评测路径。</p>
            <p v-if="validation.errors[row.key]" class="mapping-error">{{ validation.errors[row.key] }}</p>
          </template></el-table-column>
        </el-table>
      </details>
      <el-alert v-if="validation.message" :title="validation.message" type="warning" :closable="false" show-icon />
      <details v-if="ignored.length" class="ignored">
        <summary>未映射 / 将忽略的字段（{{ ignored.length }} 项，预览前 20 项）</summary>
        <p class="hint">这些字段不会写入结果；请检查是否有需要手动映射的指标或命名差异。</p>
        <ul><li v-for="field in ignored.slice(0, 20)" :key="field.pointer">{{ field.path }} → {{ jsonValueLabel(field.value) }}</li></ul>
      </details>
      <p class="hint">{{ discovery.simple ? '平铺模式：未提供指标会清空。' : '复杂模式：未映射指标保留当前输入。' }} 映射到 null 会清空该项；至少选一项有效数值。字段单位须与项目配置一致。</p>
      <el-button type="primary" :disabled="disabled || reading || !validation.canApply" @click="apply">{{ pending ? '应用映射并确认忽略字段' : '重新应用选定指标' }}</el-button>
    </template>
  </section>
</template>

<style scoped>
.json-mapper { margin-bottom: 20px; padding-bottom: 20px; border-bottom: 1px solid #e5e7eb; }
.heading, .file-label { display: block; font-weight: 600; margin: 12px 0; }
.file-label input { display: block; max-width: 100%; margin-top: 8px; font-weight: normal; }
.hint { color: #6b7280; line-height: 1.6; font-size: 12px; margin: 6px 0; }
.actions, .el-alert, details, .el-button { margin-top: 12px; }
summary { cursor: pointer; font-weight: 600; padding: 6px 0; }
.mapping-error { color: #b91c1c; font-size: 12px; margin: 6px 0; }
.ignored ul { max-height: 160px; overflow: auto; padding-left: 20px; overflow-wrap: anywhere; font-size: 12px; }
</style>
