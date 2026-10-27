<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { createBatch, deleteBatch, updateBatch } from '../api/batches'
import type { ExperimentBatch } from '../api/batches'
import { getApiErrorMessage } from '../api/errors'

const props = defineProps<{ projectId: number; batches: ExperimentBatch[]; loading?: boolean; error?: string; createOnOpen?: boolean }>()
const emit = defineEmits<{ changed: []; refresh: []; busy: [value: boolean]; created: [batch: ExperimentBatch]; cancelled: [] }>()
const editing = ref<number | null>(null)
const dialog = ref(false)
const saving = ref(false)
const savedSuccessfully = ref(false)
const formRef = ref<FormInstance>()
const form = reactive({ name: '', description: '' })
const title = computed(() => {
  if (editing.value !== null) return '编辑批次'
  return props.createOnOpen ? '新建实验 · 先建立批次' : '新建批次'
})
const rules: FormRules = { name: [{ required: true, whitespace: true, message: '批次名称不能为空', trigger: 'blur' }] }

async function open(batch?: ExperimentBatch): Promise<void> {
  savedSuccessfully.value = false
  editing.value = batch?.id ?? null
  form.name = batch?.name ?? ''; form.description = batch?.description ?? ''
  dialog.value = true
  await nextTick(); formRef.value?.clearValidate()
}
async function save(): Promise<void> {
  if (saving.value || !await formRef.value?.validate().catch(() => false)) return
  saving.value = true; emit('busy', true)
  try {
    const payload = { name: form.name.trim(), description: form.description || null }
    const creating = editing.value === null
    const saved = creating ? await createBatch(props.projectId, payload) : await updateBatch(editing.value!, payload)
    savedSuccessfully.value = true
    dialog.value = false; ElMessage.success('批次已保存'); emit('changed')
    if (creating) emit('created', saved)
  } catch (error) { ElMessage.error(getApiErrorMessage(error)) }
  finally { saving.value = false; emit('busy', false) }
}
onMounted(() => { if (props.createOnOpen) void open() })
async function remove(batch: ExperimentBatch): Promise<void> {
  if (saving.value) return
  saving.value = true; emit('busy', true)
  try {
    await ElMessageBox.confirm(`确定删除批次“${batch.name}”吗？包含实验的批次不能删除。`, '删除确认', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' })
    await deleteBatch(batch.id); ElMessage.success('批次已删除'); emit('changed')
  } catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error(getApiErrorMessage(error)) }
  finally { saving.value = false; emit('busy', false) }
}
</script>

<template>
  <template v-if="!createOnOpen">
  <div class="card-actions">
    <el-button :disabled="saving" :loading="loading" @click="emit('refresh')">刷新批次</el-button>
    <el-button type="primary" :disabled="saving || loading" @click="open()">新建批次</el-button>
  </div>
  <el-alert v-if="error" :title="error" type="error" :closable="false" />
  <el-table v-else :data="batches" v-loading="loading" aria-label="实验批次列表">
    <el-table-column prop="name" label="名称" min-width="180" show-overflow-tooltip />
    <el-table-column prop="description" label="说明" min-width="200" show-overflow-tooltip />
    <el-table-column label="操作" width="140"><template #default="{ row }">
      <el-button link type="primary" :disabled="saving" @click="open(row)">编辑</el-button>
      <el-button link type="danger" :disabled="saving" @click="remove(row)">删除</el-button>
    </template></el-table-column>
  </el-table>
  </template>
  <el-dialog v-model="dialog" :title="title" width="min(520px, 92vw)" :close-on-click-modal="!saving" :close-on-press-escape="!saving" :show-close="!saving" append-to-body @close="!savedSuccessfully && emit('cancelled')">
    <p v-if="createOnOpen" class="hint">当前项目还没有批次。为第一组实验起一个名字，保存后将继续填写实验配置。</p>
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top" :disabled="saving" @submit.prevent="save">
      <el-form-item label="批次名称" prop="name"><el-input v-model="form.name" aria-label="批次名称" /></el-form-item>
      <el-form-item label="批次说明"><el-input v-model="form.description" type="textarea" :rows="3" aria-label="批次说明" /></el-form-item>
    </el-form>
    <template #footer><el-button :disabled="saving" @click="dialog = false">取消</el-button><el-button type="primary" :loading="saving" @click="save">保存批次</el-button></template>
  </el-dialog>
</template>
