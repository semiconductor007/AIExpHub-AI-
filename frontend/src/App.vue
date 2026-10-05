<template>
  <header class="app-header">
    <div class="header-content">
      <router-link to="/" class="app-name">AIExpHub</router-link>
      <nav aria-label="主导航">
        <router-link to="/" class="nav-link" exact-active-class="active">首页</router-link>
        <router-link to="/projects" class="nav-link" exact-active-class="active">项目管理</router-link>
        <router-link to="/experiments" class="nav-link" exact-active-class="active">实验管理</router-link>
        <router-link to="/compare" class="nav-link" exact-active-class="active">实验比较</router-link>
      </nav>
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
  flex-wrap: wrap;
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px 24px;
}

.app-name {
  font-size: 20px;
  font-weight: 700;
  color: #1f2937;
  text-decoration: none;
}

nav {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.nav-link {
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 14px;
  color: #6b7280;
  text-decoration: none;
}

.nav-link.active {
  color: #2563eb;
  background: #eff6ff;
  font-weight: 600;
}

.app-main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 48px 24px;
}
</style>
