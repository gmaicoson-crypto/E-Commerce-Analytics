<template>
  <aside class="sidebar">
    <div class="logo"><AppIcon name="barChart" :size="20" color="#fff" /></div>
    <nav class="nav">
      <div v-for="item in visible" :key="item.id" class="nav-wrap" @mouseenter="hovered = item.id" @mouseleave="hovered = null">
        <button class="nav-btn" :class="{ active: route.path === item.path }" @click="router.push(item.path)">
          <AppIcon :name="item.icon" :size="20" :color="route.path === item.path ? 'var(--green-dark)' : 'rgba(255,255,255,0.92)'" />
          <span v-if="item.id === 'notifications' && unreadCount > 0" class="notif-dot" />
        </button>
        <div v-if="hovered === item.id && route.path !== item.path" class="tooltip">
          {{ item.label }}<span class="tip-arrow" />
        </div>
      </div>
    </nav>
    <div class="bottom">
      <div class="avatar"><AppIcon name="user" :size="18" color="#fff" /></div>
      <button class="logout-btn" title="退出" @click="handleLogout">
        <AppIcon name="logout" :size="18" color="rgba(255,255,255,0.85)" />
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/authStore'
import { unreadCount } from '@/composables/useUnreadCount'
import AppIcon from '@/components/common/AppIcon.vue'
import type { NavItem } from '@/types'

const route  = useRoute()
const router = useRouter()
const auth   = useAuthStore()
const hovered = ref<string | null>(null)

const NAV: NavItem[] = [
  { id: 'sales',         label: '销售概览', icon: 'sales',    path: '/sales',         adminOnly: false, moduleKey: 'sales_overview' },
  { id: 'products',      label: '商品分析', icon: 'products', path: '/products',      adminOnly: false, moduleKey: 'product_analysis' },
  { id: 'users',         label: '用户分析', icon: 'users',    path: '/users',         adminOnly: false, moduleKey: 'user_analysis' },
  { id: 'orders',        label: '订单分析', icon: 'orders',   path: '/orders',        adminOnly: false, moduleKey: 'order_analysis' },
  { id: 'finance',       label: '财务概览', icon: 'finance',  path: '/finance',       adminOnly: true                                  },
  { id: 'system',        label: '系统管理', icon: 'settings', path: '/system',        adminOnly: true                                  },
  { id: 'notifications', label: '通知中心', icon: 'bell',     path: '/notifications', adminOnly: true                                  },
]

const visible = computed(() => NAV.filter(item => {
  if (item.adminOnly) return auth.isAdmin           // 仅管理员项
  if (!item.moduleKey) return true                  // 未指定 module_key → 默认显示
  return auth.hasPermission(item.moduleKey)         // admin 永远 true;employee 看 permissions
}))

async function handleLogout() {
  await auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.sidebar { width: var(--sidebar-w); min-height: 100vh; flex-shrink: 0; background: linear-gradient(180deg,#52b788,#3a9068); display: flex; flex-direction: column; align-items: center; padding: 16px 0; z-index: 10; box-shadow: 2px 0 16px rgba(52,144,104,.18); }
.logo { width:40px;height:40px;border-radius:12px;background:rgba(255,255,255,.2);display:flex;align-items:center;justify-content:center;margin-bottom:28px; }
.nav  { display:flex;flex-direction:column;gap:4px;flex:1;width:100%;padding:0 10px; }
.nav-wrap { position: relative; }
.nav-btn { width:100%;height:44px;border-radius:12px;display:flex;align-items:center;justify-content:center;background:transparent;transition:all .18s;position:relative;cursor:pointer; }
.nav-btn:hover:not(.active) { background: rgba(255,255,255,.18); }
.nav-btn.active { background:rgba(255,255,255,.95);box-shadow:0 2px 10px rgba(0,0,0,.12); }
.notif-dot { position:absolute;top:8px;right:8px;width:7px;height:7px;border-radius:99px;background:#ef4444;border:1.5px solid #fff; }
.tooltip { position:absolute;left:110%;top:50%;transform:translateY(-50%);background:var(--text1);color:#fff;font-size:12px;font-weight:600;padding:5px 10px;border-radius:7px;white-space:nowrap;pointer-events:none;z-index:100;box-shadow:0 4px 12px rgba(0,0,0,.2); }
.tip-arrow { position:absolute;right:100%;top:50%;transform:translateY(-50%);border-width:5px;border-style:solid;border-color:transparent var(--text1) transparent transparent; }
.bottom { display:flex;flex-direction:column;align-items:center;gap:8px;padding:0 10px;width:100%; }
.avatar { width:36px;height:36px;border-radius:99px;background:rgba(255,255,255,.25);display:flex;align-items:center;justify-content:center;border:2px solid rgba(255,255,255,.5); }
.logout-btn { width:44px;height:36px;border-radius:10px;display:flex;align-items:center;justify-content:center;background:transparent;transition:background .15s;cursor:pointer; }
.logout-btn:hover { background:rgba(255,255,255,.18); }
</style>
