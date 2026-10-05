<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <el-card shadow="never" class="not-found-card">
    <section class="page-heading">
      <p class="error-code">404</p>
      <h1>页面不存在</h1>
      <p>当前地址无对应页面。</p>
    </section>
    <el-button type="primary" @click="router.push('/')">返回首页</el-button>
  </el-card>
</template>

<style scoped>
.not-found-card { max-width: 640px; margin: 0 auto; text-align: center; }
.page-heading .error-code { margin: 12px 0 16px; color: #409eff; font-size: 48px; font-weight: 700; }
</style>
