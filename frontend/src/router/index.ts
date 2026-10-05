import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import ProjectManagementView from '../views/ProjectManagementView.vue'
import ExperimentManagementView from '../views/ExperimentManagementView.vue'
import ExperimentComparisonView from '../views/ExperimentComparisonView.vue'
import NotFoundView from '../views/NotFoundView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomeView, meta: { title: 'AIExpHub' } },
    { path: '/projects', component: ProjectManagementView, meta: { title: '项目管理' } },
    { path: '/experiments', component: ExperimentManagementView, meta: { title: '实验管理' } },
    { path: '/compare', component: ExperimentComparisonView, meta: { title: '实验比较' } },
    { path: '/:pathMatch(.*)*', component: NotFoundView, meta: { title: '页面不存在' } },
  ],
})

router.afterEach(to => {
  const title = typeof to.meta.title === 'string' ? to.meta.title : 'AIExpHub'
  document.title = title === 'AIExpHub' ? title : `${title} | AIExpHub`
})

export default router
