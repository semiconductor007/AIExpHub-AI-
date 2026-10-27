<script setup lang="ts">
import { nextTick, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import type { Experiment, ExperimentPayload } from '../api/experiments'
import type { ExperimentBatch } from '../api/batches'
import { copyExperimentDraft } from '../utils/experiment-copy'
import { parseParameterObject } from '../utils/experiment-parameters'
import ExperimentParametersEditor from './ExperimentParametersEditor.vue'

export interface ExperimentDraft {
  editingId: number | null
  batchId: number
  payload: ExperimentPayload
}

const props = defineProps<{ batches: ExperimentBatch[]; submitting?: boolean }>()
const emit = defineEmits<{ save: [draft: ExperimentDraft] }>()

const visible = ref(false)
const editingId = ref<number | null>(null)
const copyingFrom = ref('')
const batchId = ref<number | null>(null)
const formRef = ref<FormInstance>()
const form = reactive({ experiment_no: '', model_name: '', parameters: '{}', notes: '' })

const rules: FormRules<typeof form> = {
  experiment_no: [{ required: true, trigger: 'blur', validator: (_rule, value: unknown, callback) => {
    callback(typeof value === 'string' && value.trim() ? undefined : new Error('实验编号不能为空'))
  } }],
  model_name: [{ required: true, trigger: 'blur', validator: (_rule, value: unknown, callback) => {
    callback(typeof value === 'string' && value.trim() ? undefined : new Error('模型名称不能为空'))
  } }],
  parameters: [{ required: true, trigger: 'blur', validator: (_rule, value: unknown, callback) => {
    try {
      if (typeof value !== 'string') throw new Error('实验参数必须是合法的 JSON 对象。')
      parseParameterObject(value)
      callback()
    } catch (error: unknown) { callback(error instanceof Error ? error : new Error('实验参数校验失败')) }
  } }],
}

const title = () => copyingFrom.value ? '复制实验配置' : editingId.value === null ? '新建实验' : '编辑实验'

async function open(experiment?: Experiment, options: { copyingFrom?: string; batchId?: number | null } = {}): Promise<void> {
  const copying = options.copyingFrom ?? ''
  copyingFrom.value = copying
  editingId.value = copying ? null : experiment?.id ?? null
  batchId.value = options.batchId ?? experiment?.batch_id ?? null
  if (copying && experiment) Object.assign(form, copyExperimentDraft(experiment))
  else {
    form.experiment_no = experiment?.experiment_no ?? ''
    form.model_name = experiment?.model_name ?? ''
    form.parameters = experiment ? JSON.stringify(experiment.parameters, null, 2) : '{}'
    form.notes = experiment?.notes ?? ''
  }
  visible.value = true
  await nextTick()
  formRef.value?.clearValidate()
}

function close(): void {
  if (!props.submitting) visible.value = false
}

async function submit(): Promise<void> {
  if (props.submitting || !formRef.value) return
  if (batchId.value === null) { ElMessage.error('请选择实验所属批次'); return }
  if (!await formRef.value.validate().catch(() => false)) return
  try {
    const parameters = parseParameterObject(form.parameters)
    emit('save', {
      editingId: editingId.value,
      batchId: batchId.value,
      payload: {
        experiment_no: form.experiment_no.trim().toUpperCase(),
        model_name: form.model_name.trim(),
        parameters,
        notes: form.notes === '' ? null : form.notes,
      },
    })
  } catch (error: unknown) {
    ElMessage.error(error instanceof Error ? error.message : '实验参数校验失败')
  }
}

defineExpose({ open, close })
</script>

<template>
  <el-dialog v-model="visible" :title="title()" width="min(600px, 92vw)"
             :close-on-click-modal="!submitting" :close-on-press-escape="!submitting" :show-close="!submitting">
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top" :disabled="submitting" @submit.prevent="submit">
      <el-alert v-if="copyingFrom" :title="`来自 ${copyingFrom}，请填写新编号。实验结果不会复制。`" type="info" :closable="false" />
      <el-form-item v-if="editingId === null" label="所属批次（必选）" required>
        <el-select v-model="batchId" aria-label="实验所属批次" placeholder="请选择所属批次">
          <el-option v-for="batch in batches" :key="batch.id" :label="batch.name" :value="batch.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="实验编号" prop="experiment_no"><el-input v-model="form.experiment_no" aria-label="实验编号" /></el-form-item>
      <el-form-item label="模型名称" prop="model_name"><el-input v-model="form.model_name" aria-label="模型名称" /></el-form-item>
      <el-form-item label="实验参数" prop="parameters"><ExperimentParametersEditor v-model="form.parameters" :disabled="submitting" /></el-form-item>
      <el-form-item label="备注（可选）" prop="notes"><el-input v-model="form.notes" type="textarea" :rows="2" aria-label="备注" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button :disabled="submitting" @click="close">取消</el-button>
      <el-button type="primary" :loading="submitting" :disabled="submitting" @click="submit">保存实验</el-button>
    </template>
  </el-dialog>
</template>
