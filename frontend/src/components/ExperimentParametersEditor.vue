<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  formatParameterObject,
  parameterRowsFromObject,
  parameterRowsToObject,
  parameterTypeOptions,
  parseParameterObject,
  type ParameterRowValue,
  type ParameterValueType,
} from '../utils/experiment-parameters'

const props = defineProps<{ modelValue: string; disabled?: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

interface EditableParameterRow extends ParameterRowValue { id: number }

const rows = ref<EditableParameterRow[]>([])
const advancedOpen = ref(false)
const advancedText = ref('')
const error = ref('')
let nextRowId = 1
let lastEmittedValue: string | null = null

const hasRows = computed(() => rows.value.length > 0)

function createRow(value: ParameterRowValue = { key: '', type: 'text', value: '' }): EditableParameterRow {
  return { ...value, id: nextRowId++ }
}

function syncFromText(text: string): void {
  advancedText.value = text
  try {
    const object = parseParameterObject(text, true)
    rows.value = parameterRowsFromObject(object).map(createRow)
    error.value = ''
    if (rows.value.some(row => row.type === 'json')) advancedOpen.value = true
  } catch (exception) {
    rows.value = []
    error.value = exception instanceof Error ? exception.message : '实验参数格式无效。'
    advancedOpen.value = true
  }
}

watch(() => props.modelValue, value => {
  if (value === lastEmittedValue) {
    lastEmittedValue = null
    return
  }
  syncFromText(value)
}, { immediate: true })

function emitValue(value: string): void {
  lastEmittedValue = value
  advancedText.value = value
  emit('update:modelValue', value)
}

function syncRowsToModel(): void {
  try {
    const object = parameterRowsToObject(rows.value)
    error.value = ''
    emitValue(formatParameterObject(object))
  } catch (exception) {
    error.value = exception instanceof Error ? exception.message : '实验参数格式无效。'
    lastEmittedValue = ''
    emit('update:modelValue', '')
  }
}

function addRow(): void {
  if (props.disabled) return
  rows.value.push(createRow())
  error.value = ''
  advancedOpen.value = false
  syncRowsToModel()
}

function removeRow(index: number): void {
  if (props.disabled) return
  rows.value.splice(index, 1)
  syncRowsToModel()
}

function updateRow(): void {
  if (props.disabled) return
  syncRowsToModel()
}

function handleTypeChange(row: EditableParameterRow, type: ParameterValueType): void {
  row.type = type
  if (type === 'boolean' && row.value !== 'true' && row.value !== 'false') row.value = 'true'
  if (type === 'json' && !row.value.trim()) row.value = 'null'
  updateRow()
}

function handleAdvancedInput(value: string): void {
  advancedText.value = value
  error.value = ''
  lastEmittedValue = value
  emit('update:modelValue', value)
}

function applyAdvanced(): void {
  try {
    const object = parseParameterObject(advancedText.value)
    rows.value = parameterRowsFromObject(object).map(createRow)
    error.value = ''
    emitValue(formatParameterObject(object))
    ElMessage.success('已应用 JSON 参数，可继续检查或修改。')
  } catch (exception) {
    error.value = exception instanceof Error ? exception.message : '实验参数格式无效。'
  }
}

function toggleAdvanced(event: Event): void {
  advancedOpen.value = (event.currentTarget as HTMLDetailsElement).open
}
</script>

<template>
  <section class="parameter-editor" aria-label="实验参数编辑器">
    <p class="hint">可直接添加参数；复杂配置可展开高级 JSON。</p>
    <div v-if="hasRows" class="parameter-list" aria-label="参数列表">
      <div class="parameter-row parameter-row-heading" aria-hidden="true">
        <span>参数名</span><span>参数值</span><span>类型</span><span></span>
      </div>
      <div v-for="(row, index) in rows" :key="row.id" class="parameter-row">
        <el-input v-model="row.key" :disabled="disabled" aria-label="参数名" placeholder="例如 learning_rate" @input="updateRow" />
        <el-select v-if="row.type === 'boolean'" v-model="row.value" :disabled="disabled" aria-label="参数值" @change="updateRow">
          <el-option label="true" value="true" />
          <el-option label="false" value="false" />
        </el-select>
        <el-input v-else v-model="row.value" :disabled="disabled" aria-label="参数值" :placeholder="row.type === 'json' ? '{...}' : '请输入参数值'" @input="updateRow" />
        <el-select :model-value="row.type" :disabled="disabled" aria-label="参数值类型" @change="handleTypeChange(row, $event)">
          <el-option v-for="option in parameterTypeOptions" :key="option.value" :label="option.label" :value="option.value" />
        </el-select>
        <el-button text type="danger" :disabled="disabled" aria-label="删除参数" @click="removeRow(index)">删除</el-button>
      </div>
    </div>
    <p v-else class="parameter-empty">暂无参数，请添加参数或使用高级 JSON。</p>
    <el-button plain :disabled="disabled" @click="addRow">添加参数</el-button>
    <p v-if="error" class="parameter-error" role="alert">{{ error }}</p>
    <details class="advanced-parameters" :open="advancedOpen" @toggle="toggleAdvanced">
      <summary>高级 JSON 参数</summary>
      <p class="hint">适合嵌套对象、数组或直接粘贴外部配置。保存前仍会校验必须是非空 JSON 对象。</p>
      <el-input :model-value="advancedText" type="textarea" :rows="7" :disabled="disabled" aria-label="高级 JSON 参数" @update:model-value="handleAdvancedInput" />
      <el-button type="primary" plain :disabled="disabled || !advancedText.trim()" @click="applyAdvanced">应用 JSON 到参数表格</el-button>
    </details>
  </section>
</template>

<style scoped>
.parameter-editor { width: 100%; }
.hint { margin: 0 0 10px; color: #6b7280; font-size: 12px; line-height: 1.6; }
.parameter-list { display: grid; gap: 8px; margin-bottom: 10px; }
.parameter-row { display: grid; grid-template-columns: minmax(130px, 1fr) minmax(150px, 1.3fr) 110px 52px; gap: 8px; align-items: center; }
.parameter-row-heading { color: #64748b; font-size: 12px; padding: 0 12px; }
.parameter-empty { margin: 0 0 10px; padding: 10px 12px; border: 1px dashed #cbd5e1; border-radius: 6px; color: #64748b; font-size: 13px; }
.parameter-error { margin: 8px 0 0; color: #b91c1c; font-size: 13px; line-height: 1.5; }
.advanced-parameters { margin-top: 14px; padding: 2px 12px 12px; border: 1px solid #e5e7eb; border-radius: 6px; background: #fafafa; }
.advanced-parameters summary { cursor: pointer; padding: 8px 0; color: #475569; font-weight: 600; }
.advanced-parameters .el-button { margin-top: 10px; }
@media (max-width: 560px) {
  .parameter-row { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
  .parameter-row-heading { display: none; }
  .parameter-row .el-select { min-width: 0; }
  .parameter-row .el-button { justify-self: start; }
}
</style>
