<template>
  <div v-if="renderedEntries.length > 0" class="marquee">
    <div class="marquee-track" :style="{ animationDuration: dur + 's' }">
      <span v-for="(e, i) in renderedEntries" :key="`o${i}-${e.key}`" class="m-item" @click="e.onClick && e.onClick()">
        <AppIcon :name="e.icon" :size="14" :color="e.color" />
        <span class="m-text">{{ e.text }}</span>
      </span>
      <span v-for="(e, i) in renderedEntries" :key="`c${i}-${e.key}`" class="m-item" aria-hidden="true" @click="e.onClick && e.onClick()">
        <AppIcon :name="e.icon" :size="14" :color="e.color" />
        <span class="m-text">{{ e.text }}</span>
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
/* 头条通知滚动组件 */
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/authStore'
import { useRealtimeStore } from '@/stores/realtimeStore'
import { api } from '@/services/api'
import { fmtMoneyCN } from '@/utils/constants'
import AppIcon from '@/components/common/AppIcon.vue'

interface Entry {
  key: string
  icon: string
  color: string
  text: string
  onClick?: () => void
}

interface Notif {
  id: number
  type: string
  title: string
  content: string
  is_read: boolean
  created_at: string | null
}

interface Highlight {
  product_name: string
  category: string
  quantity_sold: number
  sales: number
}

const auth = useAuthStore()
const realtime = useRealtimeStore()
const router = useRouter()

const NOTIF_ICON: Record<string, string> = {
  stock_alert: 'alertCircle',
  refund_alert: 'finance',
  order_alert: 'orders',
  sales_alert: 'trendUp',
}
const NOTIF_COLOR: Record<string, string> = {
  stock_alert: '#f59e0b',
  refund_alert: '#ef4444',
  order_alert: '#3b82f6',
  sales_alert: 'var(--green-dark)',
}

const entries = ref<Entry[]>([])

const dur = 30

const MIN_GROUP = 4
const renderedEntries = computed<Entry[]>(() => {
  if (entries.value.length === 0) return []
  const repeat = Math.max(1, Math.ceil(MIN_GROUP / entries.value.length))
  const arr: Entry[] = []
  for (let i = 0; i < repeat; i++) {
    for (const e of entries.value) arr.push(e)
  }
  return arr
})

async function loadEntries(): Promise<void> {
  try {
    if (auth.isAdmin) {
      const resp = await api.getNotifications(1, 5, false)
      const list: Notif[] = resp?.data ?? []
      if (list.length > 0) {
        entries.value = list.map((n) => ({
          key: `n${n.id}`,
          icon: NOTIF_ICON[n.type] ?? 'bell',
          color: NOTIF_COLOR[n.type] ?? 'var(--text2)',
          text: `${n.title} · ${n.content}`,
          onClick: () => router.push('/notifications'),
        }))
        return
      }
    }
    const hotResp = await api.getProductHighlights(7, 8)
    const hot: Highlight[] = hotResp?.data ?? []
    entries.value = hot.map((p, i) => ({
      key: `h${i}-${p.product_name}`,
      icon: 'trendUp',
      color: 'var(--green-dark)',
      text: `🔥 ${p.product_name} (${p.category}) 近 7 天售出 ${p.quantity_sold.toLocaleString()} 件 · ¥${fmtMoneyCN(p.sales, { prefix: '' })}`,
    }))
  } catch (err) {
    console.error('[HeadlineMarquee] loadEntries failed:', err)
    entries.value = []
  }
}

let pollTimer: number | undefined

onMounted(() => {
  loadEntries()
  pollTimer = window.setInterval(loadEntries, 5 * 60 * 1000)
})

onBeforeUnmount(() => {
  if (pollTimer !== undefined) window.clearInterval(pollTimer)
})

watch(() => realtime.counters.notification, loadEntries)
watch(() => realtime.counters.order, loadEntries)
</script>

<style scoped>
.marquee {
  flex: 0 1 670px;
  min-width: 0;
  max-width: 670px;
  overflow: hidden;
  height: 36px;
  background: var(--bg);
  border-radius: 10px;
  display: flex;
  align-items: center;
}

.marquee-track {
  display: flex;
  gap: 32px;
  padding: 0 16px;
  white-space: nowrap;
  animation: m-scroll linear infinite;
  will-change: transform;
}

.marquee:hover .marquee-track {
  animation-play-state: paused;
}

.m-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text2);
  cursor: pointer;
  transition: color 0.15s;
}

.m-item:hover {
  color: var(--green-dark);
}

.m-text {
  line-height: 1;
}

@keyframes m-scroll {
  0% {
    transform: translateX(0);
  }

  100% {
    transform: translateX(-50%);
  }
}
</style>
