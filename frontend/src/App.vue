<template>
  <header class="app-header">
    <div class="header-content">
      <span class="app-name">AIExpHub</span>
      <span class="app-description">实验管理平台</span>
    </div>
  </header>
  <main class="app-main">
    <router-view />
  </main>
</template>

<style scoped>
.app-header {
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  max-width: 960px;
  margin: 0 auto;
  padding: 20px 24px;
}

.app-name {
  font-size: 20px;
  font-weight: 700;
  color: #1f2937;
}

.app-description {
  font-size: 14px;
  color: #6b7280;
}

.app-main {
  max-width: 960px;
  margin: 0 auto;
  padding: 48px 24px;
}
</style>
