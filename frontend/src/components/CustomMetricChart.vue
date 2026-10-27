<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { init, use } from 'echarts/core'
import type { EChartsType } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { CustomMetricComparison, ComparisonExperiment } from '../api/compare'
import { metricLabel } from '../api/metrics'
import type { ChartExportSpec, ChartExportTarget } from '../utils/chart-export-layout'

use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])
const props = defineProps<{ metric: CustomMetricComparison; experiments: ComparisonExperiment[]; exportDisabled?: boolean; active?: boolean }>()
const emit = defineEmits<{ 'export-chart': [target: ChartExportTarget] }>()
const experiments = computed(() => props.experiments.filter(item => item.project_id === props.metric.definition.project_id))
const hasData = computed(() => experiments.value.some(item => props.metric.values[item.id] != null))
const container = ref<HTMLDivElement | null>(null)
let chart: EChartsType | undefined
let observer: ResizeObserver | undefined
let mounted = false

function chartOption() {
  return {
    animation: false,
    grid: { left: 64, right: 32, top: 36, bottom: 72 },
    tooltip: { trigger: 'axis', confine: true, renderMode: 'richText' },
    xAxis: { type: 'category', data: experiments.value.map(item => item.experiment_no), axisLabel: { interval: 0, rotate: 25, width: 110, overflow: 'truncate' } },
    yAxis: { type: 'value', name: props.metric.definition.unit },
    series: [{ name: metricLabel(props.metric.definition), type: 'bar', barMaxWidth: 48, itemStyle: { color: '#409eff' },
      data: experiments.value.map(item => {
        const value = props.metric.values[item.id]
        return value == null ? null : { value, label: { show: props.metric.best.experiment_ids.includes(item.id), formatter: '最佳', position: 'top', color: '#166534', fontWeight: 'bold' } }
      }) }],
  }
}

function getExportSpec(target: ChartExportTarget): ChartExportSpec | null {
  const definition = props.metric.definition
  if (target.kind !== 'custom' || target.projectId !== definition.project_id || target.key !== definition.key || !hasData.value) return null
  return {
    option: chartOption(), title: `${props.metric.project_name} / ${metricLabel(definition)}`,
    description: `项目 #${definition.project_id}；指标键：${definition.key}；${definition.direction === 'max' ? '↑ 越大越好' : '↓ 越小越好'}${definition.unit ? `；单位：${definition.unit}` : ''}。仅比较该项目实验，绿色“最佳”包含并列结果；缺失值保持为空。`,
    labels: experiments.value.map(item => item.experiment_no), filename: `project-${definition.project_id}_${definition.key}`,
  }
}

defineExpose({ getExportSpec })

async function render(): Promise<void> {
  await nextTick()
  if (!mounted || !container.value || props.active === false) return
  if (!hasData.value) { chart?.clear(); return }
  chart ??= init(container.value)
  chart.setOption(chartOption(), { notMerge: true })
  chart.resize()
}

watch(() => [props.metric, props.experiments, props.active], render, { flush: 'post' })
onMounted(() => {
  mounted = true
  observer = new ResizeObserver(() => { if (container.value?.clientWidth && hasData.value) chart?.resize() })
  if (container.value) observer.observe(container.value)
  void render()
})
onBeforeUnmount(() => { mounted = false; observer?.disconnect(); chart?.dispose() })
</script>

<template>
  <section class="custom-chart">
    <div class="chart-heading"><h3>{{ metric.project_name }} / {{ metricLabel(metric.definition) }}</h3><el-button size="small" :disabled="exportDisabled || !hasData" :aria-label="`导出 ${metric.definition.name} PNG`" @click="emit('export-chart', { kind: 'custom', projectId: metric.definition.project_id, key: metric.definition.key })">导出 PNG</el-button></div>
    <p class="hint">{{ metric.definition.direction === 'max' ? '↑ 越大越好' : '↓ 越小越好' }}；仅比较该项目实验，使用独立数值轴，缺失值保持为空。</p>
    <el-empty v-if="!hasData" description="该指标暂无可比较数据" />
    <div v-show="hasData" ref="container" class="chart" role="img" :aria-label="`${metric.project_name} ${metric.definition.name} 比较柱状图`" />
  </section>
</template>

<style scoped>
.custom-chart { min-width: 0; margin: 20px 0; }
.chart-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
h3 { margin: 0 0 8px; font-size: 16px; }
.hint { color: #6b7280; line-height: 1.7; font-size: 13px; }
.chart { width: 100%; min-width: 0; height: 340px; }
</style>
