<script setup lang="ts">
import type { MetricDelta } from '../api/compare'
import { formatSignedDelta } from '../utils/metric-delta'

defineProps<{ value?: MetricDelta; unit?: string }>()
const labels = { improved: '改善', regressed: '退步', unchanged: '无变化', unavailable: '无法比较' }
const reasons = {
  baseline_project_mismatch: '基准不属于该指标项目', experiment_project_mismatch: '实验不属于该指标项目',
  baseline_result_missing: '基准未录入结果', experiment_result_missing: '实验未录入结果',
  baseline_metric_missing: '基准缺少该指标', experiment_metric_missing: '实验缺少该指标', overflow: '差值超出有限数值范围',
}
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
