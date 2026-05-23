<template>
  <div class="shell">
    <Sidebar />
    <div class="main">
      <TopBar />
      <main class="content fade-in">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'
import { RouterView } from 'vue-router'
import Sidebar from '@/components/layout/Sidebar.vue'
import TopBar from '@/components/layout/TopBar.vue'
import { useAuthStore } from '@/stores/authStore'
import { useDebouncedReload } from '@/composables/useEventStream'
import { useRealtimeStore } from '@/stores/realtimeStore'
import { refreshUnread } from '@/composables/useUnreadCount'

const auth = useAuthStore()
const realtime = useRealtimeStore()

// 应用唯一 EventSource,跟随 MainLayout 生命周期 → 登录后开,登出/路由出 MainLayout 后关
onMounted(() => {
  auth.refreshPermissions()
  realtime.connect()
  if (auth.isAdmin) refreshUnread()
})
onBeforeUnmount(() => {
  realtime.disconnect()
})

// notification 事件(create/delete/update)触发未读数 refetch
useDebouncedReload(['notification'], () => {
  if (auth.isAdmin) refreshUnread()
})
</script>

<style scoped>
.shell {
  display: flex;
  width: 100%;
  height: 100vh;
  overflow: hidden;
}

.main {
  display: flex;
  flex: 1;
  flex-direction: column;
  overflow: hidden;
}

.content {
  flex: 1;
  overflow: auto;
  padding: 24px 28px;
}
</style>
