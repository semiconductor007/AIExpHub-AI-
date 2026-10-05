<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getHealth } from '../api/health'
import type { HealthResponse } from '../api/health'

const state = ref<'loading' | 'healthy' | 'unavailable'>('loading')
const health = ref<HealthResponse | null>(null)
const router = useRouter()
const entries = [
  { title: '项目管理', description: '创建实验项目与批次，组织实验工作。', path: '/projects' },
  { title: '实验管理', description: '维护模型实验、参数和评测结果。', path: '/experiments' },
  { title: '实验比较', description: '跨项目选择实验，对比指标并查看可视化结果。', path: '/compare' },
]

async function checkHealth(): Promise<void> {
  state.value = 'loading'
  health.value = null
  try {
    const response = await getHealth()
    if (response.status !== 'ok') {
      throw new Error('Backend health check did not report ok')
    }
    health.value = response
    state.value = 'healthy'
  } catch {
    state.value = 'unavailable'
  }
}

onMounted(checkHealth)
</script>

<template>
  <div class="home-content">
    <section class="page-heading">
      <h1>AIExpHub</h1>
      <p class="subtitle">AI 模型实验结果管理与可视化分析平台</p>
      <p class="description">
        用于管理实验项目、批次、模型参数和评测结果，并支持跨实验比较与指标可视化。
      </p>
    </section>

    <section class="quick-entries" aria-label="功能入口">
      <el-card v-for="entry in entries" :key="entry.path" shadow="never" class="entry-card">
        <h2>{{ entry.title }}</h2>
        <p>{{ entry.description }}</p>
        <el-button type="primary" @click="router.push(entry.path)">进入{{ entry.title }}</el-button>
      </el-card>
    </section>

    <el-card shadow="never" class="health-card">
      <template #header>
        <h2>后端服务状态</h2>
      </template>
      <div class="health-content">
        <div role="status" aria-live="polite" :aria-busy="state === 'loading'">
          <el-tag v-if="state === 'loading'" type="info">正在连接后端服务...</el-tag>
          <el-tag v-else-if="state === 'healthy'" type="success">服务正常</el-tag>
          <el-tag v-else type="danger">后端服务不可用</el-tag>
          <p v-if="state === 'healthy' && health" class="service-name">{{ health.service }}</p>
          <p v-else-if="state === 'unavailable'" class="status-hint">
            请确认后端服务已启动，然后重新检测。
          </p>
        </div>
        <el-button :loading="state === 'loading'" :disabled="state === 'loading'" @click="checkHealth">
          重新检测
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.home-content { max-width: 1040px; margin: 0 auto; }
.quick-entries { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 280px), 1fr)); gap: 20px; margin-bottom: 24px; }
.entry-card :deep(.el-card__body) { display: flex; flex-direction: column; gap: 16px; height: 100%; }
.entry-card h2 { margin: 0; font-size: 18px; }
.entry-card p { margin: 0; color: #6b7280; line-height: 1.7; }
.entry-card .el-button { align-self: flex-start; margin-top: auto; }

.subtitle {
  margin: 0 0 16px;
  font-size: 20px;
  color: #334155;
}

.description,
.status-hint {
  color: #6b7280;
  line-height: 1.7;
}

.health-content {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
}

.service-name,
.status-hint {
  margin: 12px 0 0;
  overflow-wrap: anywhere;
}
</style>
