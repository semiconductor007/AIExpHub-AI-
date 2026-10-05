<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getHealth } from '../api/health'
import type { HealthResponse } from '../api/health'

const state = ref<'loading' | 'healthy' | 'unavailable'>('loading')
const health = ref<HealthResponse | null>(null)

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
  <section class="introduction">
    <h1>AIExpHub</h1>
    <p class="subtitle">AI 模型实验结果管理平台</p>
    <p class="description">
      用于管理实验项目、实验批次、模型参数、实验结果与多实验比较。
    </p>
  </section>

  <el-card shadow="never">
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
</template>

<style scoped>
.introduction {
  margin-bottom: 32px;
}

h1 {
  margin: 0 0 12px;
  font-size: 32px;
}

.subtitle {
  margin: 0 0 16px;
  font-size: 20px;
}

.description,
.status-hint {
  color: #6b7280;
  line-height: 1.7;
}

h2 {
  margin: 0;
  font-size: 18px;
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
