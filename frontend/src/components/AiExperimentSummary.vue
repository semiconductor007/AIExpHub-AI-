<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { checkSummary, generateSummary, getSummaryStatus, previewSummary } from '../api/ai-summaries'
import type { AISummary, SummaryPreview, SummarySelection, SummaryStatus } from '../api/ai-summaries'
import { getApiErrorMessage } from '../api/errors'
import { affectsComparison, subscribeComparisonChanges } from '../utils/comparison-changes'
import { experimentLabel, factValues, kindLabels, sectionLabels, summaryExperiments, summaryToText } from '../utils/ai-summary'
import MetricDeltaDisplay from './MetricDeltaDisplay.vue'

const props = defineProps<{ experiments: { id: number; project_id: number }[]; baselineId: number | null; comparisonUpdatedAt: number | null }>()
const open = ref(false)
const busy = ref(false)
const generating = ref(false)
const error = ref('')
const preview = ref<SummaryPreview | null>(null)
const options = ref<SummaryPreview | null>(null)
const status = ref<SummaryStatus | null>(null)
const primary = ref<string | null>(null)
const paths = ref<string[]>([])
const summary = ref<AISummary | null>(null)
const stale = ref(false)
const checking = ref(false)
let version = 0
let disposed = false
let abort: AbortController | undefined
let checkAbort: AbortController | undefined
let checkVersion = 0
let unsubscribe: (() => void) | undefined
let savedSelection: SummarySelection | null = null
const scopeError = computed(() => props.experiments.length < 2 ? '请先选择至少两个实验。'
  : props.experiments.length > (status.value?.max_experiments ?? 10) ? '所选实验超过 AI 总结数量限制。'
    : new Set(props.experiments.map(item => item.project_id)).size > 1 ? 'AI 总结仅限同项目；当前跨项目比较可继续使用。' : '')
const selection = (): SummarySelection => ({
  experiment_ids: props.experiments.map(item => item.id), baseline_experiment_id: props.baselineId,
  primary_metric: primary.value || null, parameter_paths: [...paths.value],
})
const formattedPreview = computed(() => JSON.stringify(preview.value?.messages, null, 2))
const time = (value: string) => new Date(value).toLocaleString('zh-CN', { hour12: false })

function invalidate(): void {
  version += 1
  abort?.abort()
  checkAbort?.abort(); checkVersion += 1; checking.value = false
  busy.value = false; generating.value = false
  preview.value = null
  if (summary.value) stale.value = true
}
watch(() => JSON.stringify([props.experiments, props.baselineId]), () => { invalidate(); options.value = null })
watch([primary, paths], invalidate, { deep: true, flush: 'sync' })
// Compare responses omit parameters; verify the full backend fingerprint after a successful refresh.
watch(() => props.comparisonUpdatedAt, () => { void verifyLatest() })

async function loadPreview(): Promise<void> {
  if (busy.value || scopeError.value) return
  const request = ++version
  const controller = new AbortController(); abort = controller
  busy.value = true; error.value = ''; preview.value = null
  try {
    const [, snapshot] = await Promise.all([
      getSummaryStatus(controller.signal).then(configuration => {
        if (request === version && !disposed) status.value = configuration
      }),
      previewSummary(selection(), controller.signal),
    ])
    if (request !== version || disposed) return
    preview.value = snapshot; options.value = snapshot
    if (summary.value && summary.value.fingerprint !== snapshot.fingerprint) stale.value = true
  } catch (cause: unknown) {
    if (request === version && !controller.signal.aborted) error.value = getApiErrorMessage(cause, '总结预览失败，请重试。')
  } finally { if (request === version) busy.value = false }
}
function openSetup(): void { open.value = true; void loadPreview() }
function closeSetup(): void { if (busy.value) invalidate() }

async function generate(): Promise<void> {
  const snapshot = preview.value
  if (!snapshot || busy.value || !status.value?.ready || scopeError.value) return
  const currentSelection = selection()
  const request = ++version
  const controller = new AbortController(); abort = controller
  busy.value = true; generating.value = true; error.value = ''
  // A prior answer must never appear current while a new paid request is in flight.
  if (summary.value) stale.value = true
  try {
    const answer = await generateSummary(currentSelection, snapshot.fingerprint, crypto.randomUUID(), controller.signal)
    if (request !== version || disposed) return
    summary.value = answer; stale.value = answer.stale; savedSelection = currentSelection
    busy.value = false; generating.value = false
    open.value = false; preview.value = null
    ElMessage.success(answer.stale ? '已生成，但数据已变化，请重新预览生成。' : 'AI 总结已生成，请核对事实与建议。')
  } catch (cause: unknown) {
    if (request === version && !controller.signal.aborted) {
      error.value = getApiErrorMessage(cause, 'AI 总结生成失败。')
      preview.value = null // Every retry requires an explicit fresh preview.
    }
  } finally { if (request === version) { busy.value = false; generating.value = false } }
}

async function verifyLatest(): Promise<void> {
  if (document.visibilityState !== 'visible' || !summary.value || !savedSelection || checking.value || busy.value || stale.value) return
  const request = ++checkVersion
  const fingerprint = summary.value.fingerprint
  const controller = new AbortController(); checkAbort = controller
  checking.value = true
  try {
    const current = await checkSummary(savedSelection, fingerprint, controller.signal)
    if (request === checkVersion && !disposed && summary.value?.fingerprint === fingerprint && !current) stale.value = true
  } catch {
    if (request === checkVersion && !disposed) stale.value = true
  } finally { if (request === checkVersion) checking.value = false }
}
async function copySummary(): Promise<void> {
  if (!summary.value || checking.value) return
  // Revalidate without any paid call before copying a potentially old answer.
  await verifyLatest()
  if (!summary.value || disposed) return
  try { await navigator.clipboard.writeText(summaryToText(summary.value, stale.value)); ElMessage.success('已复制总结及快照状态。') }
  catch { ElMessage.error('无法使用剪贴板，请手动选择总结文本复制。') }
}
onMounted(() => {
  unsubscribe = subscribeComparisonChanges(change => {
    const relevant = [...props.experiments, ...(summary.value ? summaryExperiments(summary.value.data) : [])]
    if (affectsComparison(change, relevant)) invalidate()
  })
  window.addEventListener('focus', verifyLatest)
  document.addEventListener('visibilitychange', verifyLatest)
})
onBeforeUnmount(() => {
  disposed = true; invalidate(); unsubscribe?.()
  window.removeEventListener('focus', verifyLatest)
  document.removeEventListener('visibilitychange', verifyLatest)
})
</script>

<template>
  <el-card shadow="never" class="comparison-card ai-summary-card">
    <template #header><div class="card-header"><h2>AI 实验总结</h2><el-button :disabled="!!scopeError || busy" @click="openSetup">{{ summary ? '重新预览并生成' : '预览 AI 总结' }}</el-button></div></template>
    <p class="hint">DeepSeek 根据你确认的指标和参数解释实验，图表仍使用真实数据。仅点击“发送并生成”时调用模型。</p>
    <p v-if="scopeError" class="hint">{{ scopeError }}</p>
    <template v-if="summary">
      <el-alert v-if="stale || summary.stale" title="此总结已过期或尚未确认最新，请重新预览生成。下方内容对应原快照。" type="warning" :closable="false" show-icon />
      <p class="hint">AI 建议，需人工核对 · 模型：{{ summary.model }} · 快照：{{ time(summary.fetched_at) }} · 生成：{{ time(summary.generated_at) }}</p>
      <p>对应实验：{{ summaryExperiments(summary.data).map(item => item.experiment_no).join('、') }}</p>
      <p>基准：{{ summary.data.baseline_experiment_id === null ? '未选择' : experimentLabel(summary.data, summary.data.baseline_experiment_id) }} · 主指标：{{ summary.data.primary_metric ?? '未选择，逐项总结' }}</p>
      <el-button :loading="checking" :disabled="busy" @click="copySummary">复制总结与事实</el-button>
      <el-collapse><el-collapse-item title="确定性事实（后端计算，含最佳和基准差值）" name="facts">
        <div v-for="fact in summary.facts" :key="fact.id" class="fact-item">
          <strong>{{ fact.name }} {{ fact.unit }} {{ fact.direction === 'max' ? '↑' : '↓' }}</strong>
          <p>{{ factValues(fact, summary.data) }}</p>
          <p>最佳：{{ fact.best.experiment_ids.map(id => experimentLabel(summary!.data, id)).join('、') || '无' }}；值：{{ fact.best.value ?? '缺失' }}</p>
          <template v-if="fact.baseline"><div v-for="(delta, id) in fact.baseline.comparisons" :key="id">{{ experimentLabel(summary.data, Number(id)) }} 相对基准：<MetricDeltaDisplay :value="delta" :unit="fact.unit" /></div></template>
        </div>
      </el-collapse-item></el-collapse>
      <section v-for="section in summary.narrative.sections" :key="section.key" class="summary-section">
        <h3>{{ sectionLabels[section.key] }}</h3>
        <div v-for="(item, index) in section.items" :key="index" class="narrative-item">
          <el-tag size="small" :type="item.kind === 'hypothesis' ? 'warning' : 'info'">{{ kindLabels[item.kind] }}</el-tag>
          <p>{{ item.text }}</p><small class="hint">证据：{{ item.evidence_ids.join('、') }}</small>
        </div>
      </section>
      <ul class="hint"><li v-for="warning in summary.data.warnings" :key="warning">{{ warning }}</li></ul>
    </template>
  </el-card>

  <el-dialog v-model="open" title="确认 AI 总结发送范围" width="min(900px, 94vw)" :close-on-click-modal="false" @close="closeSetup">
    <el-alert v-if="status && !status.ready" :title="status.message" type="info" :closable="false" show-icon />
    <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
    <el-alert v-if="scopeError" :title="scopeError" type="warning" :closable="false" />
    <el-form label-position="top" :disabled="busy" class="summary-form">
      <el-form-item label="主评价指标（可选；未选时分别总结各指标）">
        <el-select v-model="primary" clearable placeholder="不指定主指标" aria-label="AI 总结主指标">
          <el-option v-for="metric in options?.metric_options ?? []" :key="metric.id" :value="metric.id" :label="`${metric.name} ${metric.unit}`" :disabled="!metric.comparable" />
        </el-select>
      </el-form-item>
      <el-form-item label="允许发送的参数（默认不发送；使用 JSON Pointer 精确路径）">
        <el-select v-model="paths" multiple filterable placeholder="不发送参数，仅总结指标" aria-label="允许发送的参数" :multiple-limit="128">
          <el-option v-for="path in options?.parameter_paths ?? []" :key="path" :value="path" :label="path" />
        </el-select>
      </el-form-item>
    </el-form>
    <p class="hint">只发送预览中的数据，不发送备注、日志和原始文件。跨项目、缺失值与单次实验均有分析局限；未勾选的参数不会发送。</p>
    <div v-if="preview">
      <p>使用模型：{{ preview.configured_model || '尚未配置' }}；快照：{{ time(preview.fetched_at) }}</p>
      <ul><li v-for="item in summaryExperiments(preview.data)" :key="item.id">{{ item.experiment_no }} · {{ item.model_name }} · {{ item.has_result ? '有结果' : '无结果，不补齐指标' }}</li></ul>
      <p>基准：{{ preview.data.baseline_experiment_id === null ? '未选择' : experimentLabel(preview.data, preview.data.baseline_experiment_id) }}；主指标：{{ primary || '未选择' }}；参数路径：{{ paths.length }} 项</p>
      <el-collapse><el-collapse-item title="展开核对完整发送内容（系统指令与实验数据）" name="payload"><pre class="payload">{{ formattedPreview }}</pre></el-collapse-item></el-collapse>
    </div>
    <p v-else class="hint">{{ generating ? '正在生成总结…' : busy ? '正在获取预览…' : '请更新发送预览，核对后再生成。' }}</p>
    <p class="hint">调用可能产生费用。失败不自动重试；超时或取消不保证服务商停止处理或不计费。</p>
    <template #footer><div class="dialog-actions">
      <el-button @click="open = false">{{ generating ? '取消等待' : '关闭' }}</el-button>
      <el-button :disabled="busy || !!scopeError" :loading="busy && !generating" @click="loadPreview">更新发送预览</el-button>
      <el-button type="primary" :disabled="!preview || !status?.ready || !!scopeError || busy" :loading="generating" @click="generate">发送并生成</el-button>
    </div></template>
  </el-dialog>
</template>

<style scoped>
.hint { color: #6b7280; line-height: 1.7; overflow-wrap: anywhere; }
.summary-form { margin-top: 16px; }
.payload { white-space: pre-wrap; overflow-wrap: anywhere; max-height: 360px; overflow-y: auto; padding: 12px; background: #f6f8fa; }
.summary-section { margin-top: 24px; }
.narrative-item { margin-bottom: 16px; overflow-wrap: anywhere; }
.narrative-item p { white-space: pre-wrap; line-height: 1.8; margin: 6px 0; }
.fact-item { border-bottom: 1px solid #ebeef5; padding: 12px 0; overflow-wrap: anywhere; }
.dialog-actions { display: flex; justify-content: flex-end; flex-wrap: wrap; gap: 8px; }
.dialog-actions .el-button { margin-left: 0; }
</style>
