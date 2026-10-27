<script setup lang="ts">
import { computed, onBeforeUnmount, ref, shallowRef, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { MetricDefinition } from '../api/metrics'
import { metricLabel } from '../api/metrics'
import { readJsonFile } from '../utils/json-files'
import { defaultMetricChoices, inspectMetricJson, jsonValueLabel, validateMetricChoices } from '../utils/json-metrics'
import type { MetricDiscovery } from '../utils/json-metrics'
import ResultMappingTemplates from './ResultMappingTemplates.vue'
import { captureMappings, templateChoices } from '../utils/mapping-templates'
import type { MappingTemplate } from '../utils/mapping-templates'

const props = defineProps<{ projectId: number; metrics: MetricDefinition[]; disabled?: boolean }>()
const emit = defineEmits<{ applied: [values: Record<string, number | null>, replace: boolean]; blocked: [value: boolean]; reading: [value: boolean] }>()
const text = ref('')
const discovery = shallowRef<MetricDiscovery | null>(null)
const choices = ref<Record<string, string | null>>({})
const error = ref('')
const fileError = ref('')
const reading = ref(false)
const pending = ref(false)
const templateBusy = ref(false)
const activeTemplate = shallowRef<MappingTemplate | null>(null)
const missingTemplateMetrics = ref<string[]>([])
const missingAccepted = ref(false)
const templateArrayKeys = ref<string[]>([])
const previewVersion = ref(0)
const advancedOpen = ref(false)
const simpleMode = computed(() => !!discovery.value?.simple && !activeTemplate.value)
const locked = computed(() => !!props.disabled || reading.value || templateBusy.value)
let readRequest = 0
let active = true
const validation = computed(() => discovery.value ? validateMetricChoices(discovery.value, props.metrics, choices.value) : null)
const canApply = computed(() => !!validation.value?.canApply && (!missingTemplateMetrics.value.length || missingAccepted.value) && !templateArrayKeys.value.length)
const templateCapture = computed(() => {
  if (!discovery.value || pending.value || !canApply.value) return { bindings: null, reason: '先核对并应用有效映射，再保存模板。' }
  try { return { bindings: captureMappings(props.metrics, discovery.value, choices.value), reason: '' } }
  catch (exception) { return { bindings: null, reason: (exception as Error).message } }
})
const ignored = computed(() => discovery.value?.fields.filter(field => field.leaf && !validation.value?.used.has(field.pointer)) ?? [])
const options = computed(() => [
  { label: simpleMode.value ? '不映射（平铺模式清空该项）' : '不映射（保留当前输入）', value: '__skip__' },
  ...(discovery.value?.fields.map(field => ({ label: `${field.path} → ${jsonValueLabel(field.value)}`, value: field.pointer })) ?? []),
  ...[...new Set(Object.values(choices.value))].filter((pointer): pointer is string => !!pointer && !discovery.value?.fields.some(field => field.pointer === pointer))
    .map(pointer => ({ label: `路径不存在：${pointer}`, value: pointer, disabled: true })),
])
const blocked = computed(() => reading.value || templateBusy.value || !!fileError.value || !!error.value || (text.value.trim() !== '' && pending.value))
watch(blocked, value => emit('blocked', value), { immediate: true, flush: 'sync' })
watch(() => reading.value || templateBusy.value, value => emit('reading', value), { flush: 'sync' })
watch([discovery, simpleMode], ([currentDiscovery, currentSimpleMode]) => {
  if (currentDiscovery && !currentSimpleMode) advancedOpen.value = true
}, { flush: 'sync' })

function apply(showMessage = true): void {
  if (locked.value || !discovery.value || !canApply.value || !validation.value) return
  emit('applied', validation.value.values, simpleMode.value)
  pending.value = false
  if (showMessage) ElMessage.success('已按选定路径填入指标；可继续手动修正后保存。')
}

function inspect(autoFill = true): void {
  previewVersion.value += 1
  discovery.value = null
  error.value = ''
  fileError.value = ''
  missingTemplateMetrics.value = []
  missingAccepted.value = false
  templateArrayKeys.value = []
  pending.value = !!text.value.trim()
  if (!text.value.trim()) return
  try {
    discovery.value = inspectMetricJson(text.value, props.metrics)
    if (activeTemplate.value) {
      const matches = templateChoices(activeTemplate.value, props.metrics, discovery.value)
      choices.value = matches.choices
      missingTemplateMetrics.value = matches.missing
      templateArrayKeys.value = [...matches.arrayBlocked]
    } else choices.value = defaultMetricChoices(discovery.value, props.metrics)
    if (autoFill && simpleMode.value && canApply.value && !locked.value) apply(false)
  } catch (exception) { error.value = exception instanceof SyntaxError ? '请输入合法 JSON，字段名需使用双引号。原输入未被覆盖。' : (exception as Error).message }
}
watch(text, () => inspect(), { flush: 'sync' })
watch(() => props.metrics, () => inspect(false))

function selectTemplate(template: MappingTemplate | null): void {
  activeTemplate.value = template
  advancedOpen.value = true
  inspect(false)
}

function savedTemplate(template: MappingTemplate): void {
  activeTemplate.value = template
  advancedOpen.value = true
  missingTemplateMetrics.value = []
  missingAccepted.value = false
}

function toggleAdvanced(event: Event): void {
  advancedOpen.value = (event.currentTarget as HTMLDetailsElement).open
}

function select(key: string, pointer: unknown): void {
  choices.value[key] = typeof pointer === 'string' && pointer !== '__skip__' ? pointer : ''
  templateArrayKeys.value = templateArrayKeys.value.filter(item => item !== key)
  pending.value = true
}

async function chooseFile(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file || locked.value) return
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
      if (simpleMode.value && canApply.value && !fileError.value) apply(false)
    }
    input.value = ''
  }
}
onBeforeUnmount(() => { active = false; readRequest += 1 })
</script>

<template>
  <section class="json-mapper" aria-label="JSON 指标识别与映射">
    <label class="heading">JSON 指标录入（可选）</label>
    <p class="hint">平铺指标 JSON 会自动填入下方表单；复杂 JSON 可展开高级录入进行映射。</p>
    <label class="file-label">选择结果 JSON 文件（最多 1 MiB）<input type="file" accept=".json,application/json" aria-label="结果 JSON 文件" :disabled="locked" @change="chooseFile" /></label>
    <el-alert v-if="fileError" :title="fileError" type="error" show-icon @close="fileError = ''" />
    <el-input v-model="text" aria-label="结果 JSON" type="textarea" :rows="5" :disabled="locked" placeholder='{"evaluation":{"accuracy":0.91,"loss":0.2},"model":"ResNet18","logs":["训练完成"]}' />
    <div class="actions"><el-button :disabled="locked || !text" @click="text = ''">清空 JSON，继续手动录入</el-button></div>
    <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
    <template v-if="discovery && validation">
      <p class="hint" aria-live="polite">{{ simpleMode && !pending ? '已自动填入，可核对下方指标。' : pending ? '映射待确认；应用前不会改变下方指标。' : '已应用映射；保存采用下方手动修正后的值。' }}</p>
    </template>
    <details class="advanced-entry" :open="advancedOpen" @toggle="toggleAdvanced">
      <summary>高级录入：项目映射模板与复杂 JSON</summary>
      <ResultMappingTemplates :project-id="projectId" :bindings="templateCapture.bindings" :save-reason="templateCapture.reason"
                              :disabled="!!disabled || reading" @selected="selectTemplate" @saved="savedTemplate" @busy="templateBusy = $event" />
      <template v-if="discovery && validation">
        <el-alert v-if="missingTemplateMetrics.length && !missingAccepted" :title="`模板指标已失效：${missingTemplateMetrics.join('、')}。不会按同名指标重新绑定。`" type="error" :closable="false" show-icon />
        <el-button v-if="missingTemplateMetrics.length && !missingAccepted" :disabled="locked" @click="missingAccepted = true; pending = true">确认忽略已失效指标</el-button>
        <el-alert v-if="templateArrayKeys.length" :title="`模板路径进入了数组：${templateArrayKeys.join('、')}。请手动重新选择来源或不映射。`" type="error" :closable="false" show-icon />
        <details :open="!simpleMode">
          <summary>指标路径映射</summary>
          <el-table :data="metrics" row-key="key" aria-label="指标路径映射列表" max-height="340">
            <el-table-column label="项目指标" min-width="150"><template #default="{ row }">{{ metricLabel(row) }}<p class="hint">{{ row.key }} · {{ row.lower_bound ?? '不限' }} ～ {{ row.upper_bound ?? '不限' }}</p></template></el-table-column>
            <el-table-column label="源字段（可搜索其他字段）" min-width="320"><template #default="{ row }">
              <el-select-v2 :key="`${previewVersion}-${row.key}`" :model-value="choices[row.key] === '' ? '__skip__' : choices[row.key]" :options="options" filterable :disabled="locked" :aria-label="`${row.key} 来源字段`" placeholder="多个候选，请选择或不映射" @change="select(row.key, $event)" />
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
        <p class="hint">{{ simpleMode ? '平铺模式：未提供指标会清空。' : '模板 / 复杂模式：未映射指标保留当前输入。' }} 映射到 null 会清空该项；至少选一项有效数值。字段单位须与项目配置一致。</p>
        <el-button type="primary" :disabled="locked || !canApply" @click="apply">{{ pending ? '应用映射并确认忽略字段' : '重新应用选定指标' }}</el-button>
      </template>
    </details>
  </section>
</template>

<style scoped>
.json-mapper { margin-bottom: 20px; padding-bottom: 20px; border-bottom: 1px solid #e5e7eb; }
.heading, .file-label { display: block; font-weight: 600; margin: 12px 0; }
.file-label input { display: block; max-width: 100%; margin-top: 8px; font-weight: normal; }
.hint { color: #6b7280; line-height: 1.6; font-size: 12px; margin: 6px 0; }
.actions, .el-alert, details, .el-button { margin-top: 12px; }
.advanced-entry { border: 1px solid #e5e7eb; border-radius: 6px; padding: 2px 12px 12px; background: #fafafa; }
.advanced-entry > summary { color: #475569; }
summary { cursor: pointer; font-weight: 600; padding: 6px 0; }
.mapping-error { color: #b91c1c; font-size: 12px; margin: 6px 0; }
.ignored ul { max-height: 160px; overflow: auto; padding-left: 20px; overflow-wrap: anywhere; font-size: 12px; }
</style>
