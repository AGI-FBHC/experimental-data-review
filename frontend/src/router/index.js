import { createRouter, createWebHistory } from 'vue-router'
import Review from '../views/Review.vue'

const routes = [
  {
    path: '/',
    redirect: '/review'
  },
  {
    path: '/review',
    name: 'Review',
    component: Review
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
