<script setup lang="ts">
import type { MetricDelta } from '../api/compare'
import { formatSignedDelta } from '../utils/metric-delta'
import { deltaReasonLabels as reasons, deltaStatusLabels as labels } from '../utils/comparison-export'

defineProps<{ value?: MetricDelta; unit?: string }>()
</script>

<template>
  <div class="delta" :data-status="value?.status">
    <template v-if="value && value.delta !== null">
      <span :title="String(value.delta)">Δ {{ formatSignedDelta(value.delta) }}{{ unit ? ` ${unit}` : '' }}</span>
      <el-tag :type="value.status === 'improved' ? 'success' : value.status === 'regressed' ? 'danger' : 'info'" size="small">{{ labels[value.status] }}</el-tag>
    </template>
    <span v-else class="unavailable">无法比较{{ value?.reason ? `：${reasons[value.reason]}` : '' }}</span>
  </div>
</template>

<style scoped>
.delta { display: flex; flex-wrap: wrap; gap: 4px 6px; align-items: center; font-size: 12px; margin-top: 6px; }
.unavailable { color: #6b7280; line-height: 1.6; }
</style>
