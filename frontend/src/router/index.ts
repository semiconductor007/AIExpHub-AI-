import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import ProjectManagementView from '../views/ProjectManagementView.vue'
import ExperimentManagementView from '../views/ExperimentManagementView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomeView, meta: { title: 'AIExpHub' } },
    { path: '/projects', component: ProjectManagementView, meta: { title: '项目管理' } },
    { path: '/experiments', component: ExperimentManagementView, meta: { title: '实验管理' } },
  ],
})

export default router
