<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { init, use } from 'echarts/core'
import type { ComposeOption, EChartsType } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import type { BarSeriesOption } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import type { GridComponentOption, LegendComponentOption, TooltipComponentOption } from 'echarts/components'
import type { TooltipComponentFormatterCallbackParams } from 'echarts'
import { CanvasRenderer } from 'echarts/renderers'
import type { ExperimentCompareResponse, MetricName } from '../api/compare'

use([BarChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

type ChartOption = ComposeOption<BarSeriesOption | GridComponentOption | LegendComponentOption | TooltipComponentOption>
const props = defineProps<{ result: ExperimentCompareResponse }>()
const comprehensiveMetrics: { key: MetricName; label: string }[] = [
  { key: 'accuracy', label: 'Accuracy' }, { key: 'precision', label: 'Precision' },
  { key: 'recall', label: 'Recall' }, { key: 'f1', label: 'F1' },
]
const lossMetric: { key: MetricName; label: string }[] = [{ key: 'loss', label: 'Loss' }]
const comprehensiveContainer = ref<HTMLDivElement | null>(null)
const lossContainer = ref<HTMLDivElement | null>(null)
let comprehensiveChart: EChartsType | undefined
let lossChart: EChartsType | undefined
let observer: ResizeObserver | undefined
let mounted = false

function metricValue(index: number, metric: MetricName): number | null {
  return props.result.experiments[index]?.result?.[metric] ?? null
}

function hasData(metrics: { key: MetricName }[]): boolean {
  return props.result.experiments.some((_, index) => metrics.some(metric => metricValue(index, metric.key) !== null))
}

const hasComprehensiveData = computed(() => hasData(comprehensiveMetrics))
const hasLossData = computed(() => hasData(lossMetric))

function tooltip(metrics: { key: MetricName; label: string }[]): TooltipComponentOption {
  return {
    trigger: 'axis', confine: true, renderMode: 'richText', axisPointer: { type: 'shadow' },
    formatter: (params: TooltipComponentFormatterCallbackParams): string => {
      const first = Array.isArray(params) ? params[0] : params
      if (!first) return ''
      const experiment = props.result.experiments[first.dataIndex]
      if (!experiment) return ''
      // Read the same response as the bars, including metrics omitted by a null tooltip item.
      return [experiment.experiment_no, experiment.model_name, ...metrics.map(metric =>
        `${metric.label}: ${metricValue(first.dataIndex, metric.key) ?? '-'}`,
      )].join('\n')
    },
  }
}

function series(metric: { key: MetricName; label: string }): BarSeriesOption {
  return {
    name: metric.label, type: 'bar', barMaxWidth: 48,
    data: props.result.experiments.map((experiment, index) => {
      const value = metricValue(index, metric.key)
      if (value === null) return null
      return {
        value,
        label: {
          show: props.result.best_by_metric[metric.key].experiment_ids.includes(experiment.id),
          formatter: '最佳', position: 'top', distance: 6, color: '#166534', fontWeight: 'bold',
        },
      }
    }),
  }
}

function option(metrics: { key: MetricName; label: string }[], comprehensive: boolean): ChartOption {
  return {
    animation: false,
    color: comprehensive ? ['#409eff', '#67c23a', '#e6a23c', '#a78bfa'] : ['#409eff'],
    grid: { left: 48, right: 24, top: 52, bottom: 72 },
    legend: { data: metrics.map(metric => metric.label), top: 4 },
    tooltip: tooltip(metrics),
    xAxis: {
      type: 'category', data: props.result.experiments.map(experiment => experiment.experiment_no),
      axisLabel: { interval: 0, rotate: 25, width: 110, overflow: 'truncate' },
    },
    yAxis: { type: 'value', min: 0, ...(comprehensive ? { max: 1 } : {}) },
    series: metrics.map(series),
  }
}

function resizeCharts(): void {
  if (comprehensiveContainer.value?.clientWidth && hasComprehensiveData.value) comprehensiveChart?.resize()
  if (lossContainer.value?.clientWidth && hasLossData.value) lossChart?.resize()
}

async function renderCharts(): Promise<void> {
  await nextTick()
  if (!mounted) return
  if (hasComprehensiveData.value && comprehensiveContainer.value) {
    comprehensiveChart ??= init(comprehensiveContainer.value)
    comprehensiveChart.setOption(option(comprehensiveMetrics, true), { notMerge: true })
  } else comprehensiveChart?.clear()
  if (hasLossData.value && lossContainer.value) {
    lossChart ??= init(lossContainer.value)
    lossChart.setOption(option(lossMetric, false), { notMerge: true })
  } else lossChart?.clear()
  resizeCharts()
}

watch(() => props.result, renderCharts, { flush: 'post' })
onMounted(() => {
  mounted = true
  observer = new ResizeObserver(resizeCharts)
  if (comprehensiveContainer.value) observer.observe(comprehensiveContainer.value)
  if (lossContainer.value) observer.observe(lossContainer.value)
  void renderCharts()
})
onBeforeUnmount(() => {
  mounted = false
  observer?.disconnect()
  comprehensiveChart?.dispose()
  lossChart?.dispose()
  comprehensiveChart = undefined
  lossChart = undefined
})
</script>

<template>
  <section class="comparison-charts" aria-label="可视化比较">
    <h3>综合指标比较</h3>
    <p class="chart-hint">Accuracy / Precision / Recall / F1：越大越好，范围 0–1。绿色“最佳”使用后端比较结果。</p>
    <el-empty v-if="!hasComprehensiveData" description="暂无可视化的综合指标数据" />
    <div v-show="hasComprehensiveData" ref="comprehensiveContainer" class="chart comprehensive-chart" role="img" aria-label="综合指标比较柱状图" />
    <h3>Loss 比较</h3>
    <p class="chart-hint">Loss 越小越好，独立使用从 0 开始的自适应数值轴；缺失指标保持为空。</p>
    <el-empty v-if="!hasLossData" description="暂无可视化的 Loss 数据" />
    <div v-show="hasLossData" ref="lossContainer" class="chart loss-chart" role="img" aria-label="Loss 比较柱状图" />
  </section>
</template>

<style scoped>
.comparison-charts { min-width: 0; margin-bottom: 24px; }
h3 { margin: 20px 0 8px; font-size: 16px; }
.chart-hint { margin: 0 0 12px; color: #6b7280; font-size: 13px; line-height: 1.7; }
.chart { width: 100%; min-width: 0; }
.comprehensive-chart { height: 400px; }
.loss-chart { height: 340px; }
</style>
