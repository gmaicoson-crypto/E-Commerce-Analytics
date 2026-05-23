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
/* 后台主布局组件 */
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

onMounted(() => {
  auth.refreshPermissions()
  realtime.connect()
  if (auth.isAdmin) refreshUnread()
})
onBeforeUnmount(() => {
  realtime.disconnect()
})

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
