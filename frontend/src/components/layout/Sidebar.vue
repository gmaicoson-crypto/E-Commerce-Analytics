<template>
  <aside class="sidebar">
    <div class="logo">
      <AppIcon name="barChart" :size="20" color="#fff" />
    </div>
    <nav class="nav">
      <div
        v-for="item in visible"
        :key="item.id"
        class="nav-wrap"
        @mouseenter="hovered = item.id"
        @mouseleave="hovered = null"
      >
        <button
          class="nav-btn"
          :class="{ active: route.path === item.path }"
          @click="router.push(item.path)"
        >
          <AppIcon
            :name="item.icon"
            :size="20"
            :color="
              route.path === item.path
                ? 'var(--green-dark)'
                : 'rgba(255,255,255,0.92)'
            "
          />
          <span v-if="item.id === 'notifications' && unreadCount > 0" class="notif-dot" />
        </button>
        <div v-if="hovered === item.id && route.path !== item.path" class="tooltip">
          {{ item.label }}<span class="tip-arrow" />
        </div>
      </div>
    </nav>
    <div class="bottom">
      <div class="avatar">
        <AppIcon name="user" :size="18" color="#fff" />
      </div>
      <button class="logout-btn" title="退出" @click="handleLogout">
        <AppIcon name="logout" :size="18" color="rgba(255,255,255,0.85)" />
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
/* 侧边导航组件 */
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { unreadCount } from '@/composables/useUnreadCount'
import AppIcon from '@/components/common/AppIcon.vue'
import { useAuthStore } from '@/stores/authStore'
import type { NavItem } from '@/types'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const hovered = ref<string | null>(null)

const NAV: NavItem[] = [
  {
    id: 'sales',
    label: '销售概览',
    icon: 'sales',
    path: '/sales',
    adminOnly: false,
    moduleKey: 'sales_overview',
  },
  {
    id: 'products',
    label: '商品分析',
    icon: 'products',
    path: '/products',
    adminOnly: false,
    moduleKey: 'product_analysis',
  },
  {
    id: 'users',
    label: '用户分析',
    icon: 'users',
    path: '/users',
    adminOnly: false,
    moduleKey: 'user_analysis',
  },
  {
    id: 'orders',
    label: '订单分析',
    icon: 'orders',
    path: '/orders',
    adminOnly: false,
    moduleKey: 'order_analysis',
  },
  {
    id: 'finance',
    label: '财务概览',
    icon: 'finance',
    path: '/finance',
    adminOnly: true,
  },
  {
    id: 'system',
    label: '系统管理',
    icon: 'settings',
    path: '/system',
    adminOnly: true,
  },
  {
    id: 'notifications',
    label: '通知中心',
    icon: 'bell',
    path: '/notifications',
    adminOnly: true,
  },
]

const visible = computed(() =>
  NAV.filter((item) => {
    if (item.adminOnly) {
      return auth.isAdmin
    }
    if (!item.moduleKey) {
      return true
    }
    return auth.hasPermission(item.moduleKey)
  }),
)

async function handleLogout() {
  await auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.sidebar {
  display: flex;
  flex-shrink: 0;
  flex-direction: column;
  align-items: center;
  width: var(--sidebar-w);
  min-height: 100vh;
  padding: 16px 0;
  z-index: 10;
  background: linear-gradient(180deg, #52b788, #3a9068);
  box-shadow: 2px 0 16px rgba(52, 144, 104, 0.18);
}

.logo {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  margin-bottom: 28px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.2);
}

.nav {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 4px;
  width: 100%;
  padding: 0 10px;
}

.nav-wrap {
  position: relative;
}

.nav-btn {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 44px;
  border-radius: 12px;
  background: transparent;
  cursor: pointer;
  transition: all 0.18s;
}

.nav-btn:hover:not(.active) {
  background: rgba(255, 255, 255, 0.18);
}

.nav-btn.active {
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.12);
}

.notif-dot {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 7px;
  height: 7px;
  border: 1.5px solid #fff;
  border-radius: 99px;
  background: #ef4444;
}

.tooltip {
  position: absolute;
  top: 50%;
  left: 110%;
  z-index: 100;
  padding: 5px 10px;
  border-radius: 7px;
  background: var(--text1);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  pointer-events: none;
  white-space: nowrap;
  transform: translateY(-50%);
}

.tip-arrow {
  position: absolute;
  top: 50%;
  right: 100%;
  border-style: solid;
  border-width: 5px;
  border-color: transparent var(--text1) transparent transparent;
  transform: translateY(-50%);
}

.bottom {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 0 10px;
}

.avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: 2px solid rgba(255, 255, 255, 0.5);
  border-radius: 99px;
  background: rgba(255, 255, 255, 0.25);
}

.logout-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 36px;
  border-radius: 10px;
  background: transparent;
  cursor: pointer;
  transition: background 0.15s;
}

.logout-btn:hover {
  background: rgba(255, 255, 255, 0.18);
}
</style>
