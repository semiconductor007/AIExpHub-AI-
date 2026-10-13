<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { UploadFile } from 'element-plus'
import { confirmImport, getImportTemplate, previewImport } from '../api/imports'
import type { ImportDocument, ImportPreview } from '../api/imports'
import { getApiErrorMessage } from '../api/errors'
import { downloadJson, MAX_JSON_BYTES, parseJsonText, readJsonFile } from '../utils/json-files'

const props = defineProps<{ projectId: number | null; batchId: number | null; batchName?: string; disabled?: boolean }>()
const emit = defineEmits<{ imported: [] ; busy: [value: boolean] }>()
const visible = ref(false)
const draft = ref('')
const filename = ref('')
const error = ref('')
const preview = ref<ImportPreview | null>(null)
const validatedDocument = ref<ImportDocument | null>(null)
const loading = ref(false)
const saving = ref(false)
const reading = ref(false)
const exporting = ref(false)
const editingRow = ref<number | null>(null)
const rowText = ref('')
const rowError = ref('')
let revision = 0
let readRequest = 0
const busy = computed(() => loading.value || saving.value || reading.value || exporting.value)

watch(busy, value => emit('busy', value))
watch(draft, () => { revision += 1; preview.value = null; validatedDocument.value = null; error.value = '' }, { flush: 'sync' })
watch(() => [props.projectId, props.batchId], () => {
  revision += 1; readRequest += 1; visible.value = false; draft.value = ''; filename.value = ''; editingRow.value = null
  preview.value = null; validatedDocument.value = null
})
onBeforeUnmount(() => { revision += 1; readRequest += 1 })

function parse(): ImportDocument {
  if (new Blob([draft.value]).size > MAX_JSON_BYTES) throw new Error('JSON 内容不能超过 1 MiB，请拆分后导入。')
  const value: unknown = parseJsonText(draft.value)
  if (Array.isArray(value)) return { experiments: value }
  if (typeof value !== 'object' || value === null || !('experiments' in value) || !Array.isArray(value.experiments)) {
    throw new Error('批量 JSON 必须是含 experiments 数组的对象，或直接提供实验记录数组。请参考项目模板。')
  }
  return value as ImportDocument
}

function open(): void {
  if (props.batchId === null || props.disabled || busy.value) return
  visible.value = true
}

async function readFile(file: UploadFile): Promise<void> {
  if (!file.raw || busy.value) return
  const request = ++readRequest
  reading.value = true
  error.value = ''
  preview.value = null
  validatedDocument.value = null
  try {
    const text = await readJsonFile(file.raw)
    if (request !== readRequest) return
    draft.value = text
    filename.value = file.name
  } catch (exception) {
    if (request === readRequest) error.value = exception instanceof SyntaxError ? '文件不是合法 JSON，当前草稿未被覆盖。' : (exception as Error).message
  } finally { reading.value = false }
}

async function exportTemplate(): Promise<void> {
  if (props.projectId === null || busy.value) return
  const target = props.projectId
  exporting.value = true
  try { downloadJson(await getImportTemplate(target), `AIExpHub-project-${target}-template.json`) }
  catch (exception) { ElMessage.error(getApiErrorMessage(exception, '模板下载失败')) }
  finally { exporting.value = false }
}

async function check(): Promise<void> {
  if (props.batchId === null || busy.value) return
  preview.value = null
  validatedDocument.value = null
  error.value = ''
  loading.value = true
  const target = props.batchId
  const current = revision
  try {
    const document = parse()
    const response = await previewImport(target, document)
    if (current !== revision || target !== props.batchId) return
    preview.value = response
    if (response.can_import) validatedDocument.value = document
  } catch (exception) {
    if (current === revision) error.value = exception instanceof SyntaxError ? '请输入合法 JSON。' : getApiErrorMessage(exception, exception instanceof Error ? exception.message : '预览失败')
  } finally { loading.value = false }
}

function edit(row: number): void {
  try {
    const document = parse()
    editingRow.value = row - 1
    rowText.value = JSON.stringify(document.experiments[row - 1], null, 2)
    rowError.value = ''
  } catch (exception) { error.value = (exception as Error).message }
}

function applyRow(): void {
  try {
    const document = parse()
    if (editingRow.value === null) return
    document.experiments[editingRow.value] = parseJsonText(rowText.value)
    draft.value = JSON.stringify(document, null, 2)
    editingRow.value = null
    ElMessage.info('已修正草稿，请重新校验预览。')
  } catch (exception) { rowError.value = exception instanceof SyntaxError ? '记录必须是合法 JSON。' : (exception as Error).message }
}

async function save(): Promise<void> {
  if (props.batchId === null || busy.value || !validatedDocument.value || !preview.value?.can_import) return
  saving.value = true
  error.value = ''
  const target = props.batchId
  const document = validatedDocument.value
  try {
    const created = await confirmImport(target, document)
    visible.value = false
    draft.value = ''
    filename.value = ''
    ElMessage.success(`已导入 ${created.length} 个实验及所提供的结果。`)
    emit('imported')
  } catch (exception) {
    preview.value = null
    validatedDocument.value = null
    error.value = '整批未保存，请重新校验预览，检查编号和指标定义是否变化。'
    ElMessage.error(getApiErrorMessage(exception, error.value))
  } finally { saving.value = false }
}
</script>

<template>
  <el-button :disabled="batchId === null || disabled || busy" @click="open">批量导入 JSON</el-button>
  <el-dialog v-model="visible" :title="`批量导入 / ${batchName ?? '当前批次'}`" width="min(920px,94vw)" top="4vh"
             :close-on-click-modal="!busy" :close-on-press-escape="!busy" :show-close="!busy">
    <p class="hint">只新增到当前批次，不覆盖已有实验。最多 100 条、1 MiB；预览不保存，确认时重新校验，整批成功才保存。result 为 null 或省略表示暂不录入结果。</p>
    <p class="hint">模板中的空指标为占位：请填入至少一项真实数值，或将 result 改为 null。指标定义只作核对，不会自动创建或修改项目指标。</p>
    <el-button :loading="exporting" :disabled="busy" @click="exportTemplate">下载当前项目模板</el-button>
    <el-upload drag accept=".json,application/json" :auto-upload="false" :show-file-list="false" :disabled="busy" :on-change="readFile">
      <div class="upload-label">拖入 JSON 文件，或点击选择文件</div>
      <div class="hint">{{ filename || '文件只用于填入草稿，确认前不会保存到数据库。' }}</div>
    </el-upload>
    <label for="import-json">导入草稿（可粘贴或修改）</label>
    <el-input id="import-json" v-model="draft" aria-label="批量导入 JSON" type="textarea" :rows="9" :disabled="busy" placeholder='{"experiments":[{"experiment_no":"EXP-NEW","model_name":"模型名称","parameters":{"seed":42},"result":{"accuracy":0.86}}]}' />
    <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
    <el-button class="preview-button" type="primary" :disabled="!draft.trim() || busy" :loading="loading" @click="check">校验并预览</el-button>
    <template v-if="preview">
      <el-alert :title="`共 ${preview.total} 条，${preview.valid_count} 条有效；${preview.can_import ? '核对后可确认导入' : '请修正错误后重新预览'}`" :type="preview.can_import ? 'success' : 'warning'" :closable="false" />
      <el-table :data="preview.rows" aria-label="导入预览列表" max-height="320">
        <el-table-column prop="row" label="行" width="55" />
        <el-table-column prop="experiment_no" label="规范化编号" min-width="150" show-overflow-tooltip />
        <el-table-column label="模型 / 参数 / 结果" min-width="250"><template #default="{ row }"><div v-if="row.normalized" class="preview-details">
          <p>模型：{{ row.normalized.model_name }}</p><p>参数：{{ JSON.stringify(row.normalized.parameters) }}</p>
          <p>结果：{{ row.normalized.result === null ? '未录入' : Object.entries(row.normalized.result).filter(([, value]) => value !== null).map(([key, value]) => `${key}: ${value}`).join('，') }}</p>
          <p v-if="row.normalized.notes">备注：{{ row.normalized.notes }}</p>
        </div><span v-else>请查看错误或修正原记录</span></template></el-table-column>
        <el-table-column label="校验" min-width="190"><template #default="{ row }"><span v-if="!row.errors.length">可导入</span><p v-for="message in row.errors" :key="message" class="row-error">{{ message }}</p></template></el-table-column>
        <el-table-column label="操作" width="80"><template #default="{ row }"><el-button link type="primary" :disabled="busy" @click="edit(row.row)">修正</el-button></template></el-table-column>
      </el-table>
    </template>
    <template #footer><el-button :disabled="busy" @click="visible = false">关闭</el-button><el-button type="primary" :loading="saving" :disabled="busy || !preview?.can_import || !validatedDocument" @click="save">确认导入 {{ preview?.total ?? 0 }} 条</el-button></template>
  </el-dialog>
  <el-dialog :model-value="editingRow !== null" title="修正单条记录" width="min(600px,92vw)" @update:model-value="editingRow = null">
    <p class="hint">修改该条实验的编号、模型、参数或 result 指标。应用后需重新预览。</p>
    <el-input v-model="rowText" aria-label="修正导入记录" type="textarea" :rows="12" />
    <el-alert v-if="rowError" :title="rowError" type="error" :closable="false" />
    <template #footer><el-button @click="editingRow = null">取消</el-button><el-button type="primary" @click="applyRow">应用修正</el-button></template>
  </el-dialog>
</template>

<style scoped>
.hint { color: #6b7280; line-height: 1.7; }
.upload-label { padding: 8px; font-weight: 600; }
.el-upload { margin-top: 12px; }
label { display: block; margin: 12px 0; font-weight: 600; }
.el-alert, .preview-button { margin-top: 12px; }
.preview-details { overflow-wrap: anywhere; font-size: 12px; }
.preview-details p { margin: 4px 0; }
.row-error { color: #b91c1c; margin: 4px 0; }
</style>
