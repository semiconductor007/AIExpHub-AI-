<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { deleteMappingTemplate, getMappingTemplates, renameMappingTemplate, saveMappingTemplate } from '../api/mapping-templates'
import type { MappingBinding, MappingTemplate } from '../utils/mapping-templates'
import { getApiErrorMessage } from '../api/errors'

const props = defineProps<{ projectId: number; bindings: MappingBinding[] | null; saveReason: string; disabled: boolean }>()
const emit = defineEmits<{ selected: [template: MappingTemplate | null]; saved: [template: MappingTemplate]; busy: [value: boolean] }>()
const templates = ref<MappingTemplate[]>([])
const selectedId = ref<number | null>(null)
const selected = computed(() => templates.value.find(item => item.id === selectedId.value))
const busy = ref(false)
const error = ref('')
let active = true
let request = 0
watch(busy, value => emit('busy', value), { flush: 'sync' })

async function load(): Promise<void> {
  const revision = ++request
  busy.value = true
  error.value = ''
  try {
    const data = await getMappingTemplates(props.projectId)
    if (active && revision === request) {
      templates.value = data
      if (selectedId.value !== null) {
        if (!selected.value) selectedId.value = null
        select()
      }
    }
  } catch (exception) { if (active && revision === request) error.value = getApiErrorMessage(exception, '映射模板加载失败，可重试或继续手动录入。') }
  finally { if (active && revision === request) busy.value = false }
}

function select(): void { emit('selected', selected.value ?? null) }

async function namePrompt(value = ''): Promise<string> {
  const response = await ElMessageBox.prompt('名称在当前项目内唯一，最多 100 个字符。', '映射模板名称', {
    inputValue: value, inputPlaceholder: '例如：评估脚本输出', confirmButtonText: '确定', cancelButtonText: '取消',
    inputValidator: text => !!text?.trim() && text.trim().length <= 100 || '请填写 1～100 个字符的模板名称',
  })
  return response.value.trim()
}

async function operate(action: 'create' | 'update' | 'rename' | 'delete'): Promise<void> {
  if (props.disabled || busy.value || (action !== 'create' && !selected.value)) return
  if ((action === 'create' || action === 'update') && !props.bindings) return
  const current = selected.value
  const bindings = props.bindings?.map(item => ({ ...item })) ?? null
  busy.value = true
  error.value = ''
  try {
    if (action === 'delete') {
      await ElMessageBox.confirm(`删除模板“${current!.name}”？已有实验结果不受影响。`, '删除映射模板', { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' })
      await deleteMappingTemplate(props.projectId, current!.id)
      templates.value = templates.value.filter(item => item.id !== current!.id)
      selectedId.value = null
      emit('selected', null)
    } else {
      let saved: MappingTemplate
      if (action === 'rename') saved = await renameMappingTemplate(props.projectId, current!.id, await namePrompt(current!.name))
      else {
        const name = action === 'create' ? await namePrompt() : current!.name
        if (action === 'update') await ElMessageBox.confirm(`用当前已应用的路径更新“${name}”？其他实验下次使用此模板时将读取新路径。`, '更新模板映射', { confirmButtonText: '更新', cancelButtonText: '取消' })
        saved = await saveMappingTemplate(props.projectId, name, bindings!, action === 'update' ? current!.id : undefined)
      }
      templates.value = [...templates.value.filter(item => item.id !== saved.id), saved].sort((a, b) => a.id - b.id)
      selectedId.value = saved.id
      // Renaming does not reapply paths or overwrite manual form corrections.
      if (action !== 'rename') emit('saved', saved)
    }
    ElMessage.success(action === 'delete' ? '映射模板已删除' : '映射模板已保存')
  } catch (exception) {
    if (exception !== 'cancel' && exception !== 'close') {
      error.value = getApiErrorMessage(exception, '模板操作失败，请刷新模板后重试。')
      ElMessage.error(error.value)
    }
  } finally { if (active) busy.value = false }
}

watch(() => props.projectId, () => { selectedId.value = null; emit('selected', null); void load() }, { immediate: true })
onBeforeUnmount(() => { active = false; request += 1 })
</script>

<template>
  <div class="mapping-templates">
    <label class="heading">项目映射模板（可选）</label>
    <el-select v-model="selectedId" clearable aria-label="项目映射模板" placeholder="选择已有模板，或手动映射" :disabled="disabled || busy" @change="select">
      <el-option v-for="item in templates" :key="item.id" :value="item.id" :label="item.name" />
    </el-select>
    <div class="template-actions">
      <el-button :disabled="disabled || busy" @click="load">刷新模板</el-button>
      <el-button :disabled="disabled || busy || !bindings" @click="operate('create')">另存为映射模板</el-button>
      <el-button :disabled="disabled || busy || !selected || !bindings" @click="operate('update')">更新模板映射</el-button>
      <el-button :disabled="disabled || busy || !selected" @click="operate('rename')">重命名模板</el-button>
      <el-button type="danger" plain :disabled="disabled || busy || !selected" @click="operate('delete')">删除模板</el-button>
    </div>
    <p class="hint">模板在当前项目各批次间共享，仅保存对象字段路径。选择模板后仍需预览并应用；更改映射须主动更新模板。</p>
    <p v-if="saveReason" class="hint">{{ saveReason }}</p>
    <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
  </div>
</template>

<style scoped>
.mapping-templates { padding: 12px; margin-bottom: 12px; background: #f8fafc; border-radius: 6px; }
.heading { display: block; font-weight: 600; margin-bottom: 8px; }
.template-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.template-actions .el-button { margin-left: 0; }
.hint { font-size: 12px; color: #6b7280; line-height: 1.6; }
</style>
