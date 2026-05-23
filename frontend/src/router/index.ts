/* 前端路由配置 */

import {
  createRouter,
  createWebHashHistory,
  type RouteRecordRaw,
} from 'vue-router'
import { useAuthStore } from '@/stores/authStore'

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/login' },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: 'sales',
        name: 'Sales',
        component: () => import('@/views/SalesView.vue'),
      },
      {
        path: 'products',
        name: 'Products',
        component: () => import('@/views/ProductView.vue'),
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/UserView.vue'),
      },
      {
        path: 'orders',
        name: 'Orders',
        component: () => import('@/views/OrderView.vue'),
      },
      {
        path: 'finance',
        name: 'Finance',
        component: () => import('@/views/FinanceView.vue'),
        meta: { adminOnly: true },
      },
      {
        path: 'system',
        name: 'System',
        component: () => import('@/views/SystemView.vue'),
        meta: { adminOnly: true },
      },
      {
        path: 'notifications',
        name: 'Notifications',
        component: () => import('@/views/NotificationsView.vue'),
        meta: { adminOnly: true },
      },
    ],
  },
  {
    path: '/403',
    name: '403',
    component: () => import('@/views/ErrorView.vue'),
    props: { code: 403 },
  },
  {
    path: '/:pathMatch(.*)*',
    name: '404',
    component: () => import('@/views/ErrorView.vue'),
    props: { code: 404 },
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()

  if (to.meta['requiresAuth'] && !auth.isLoggedIn) {
    return '/login'
  }

  if (to.path === '/login' && auth.isLoggedIn) {
    return '/sales'
  }

  if (to.meta['adminOnly'] && !auth.isAdmin) {
    return '/403'
  }
})

export default router
