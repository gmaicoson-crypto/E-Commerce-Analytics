<template>
  <div
    v-if="items.length > 0"
    class="ticker"
    @mouseenter="paused = true"
    @mouseleave="paused = false"
  >
    <span class="ticker-label">热卖榜</span>
    <div class="ticker-stage">
      <Transition name="flip">
        <div :key="index" class="ticker-row">
          <AppIcon name="trendUp" :size="14" color="var(--green-dark)" />
          <span class="ticker-text">
            🔥 {{ current.product_name }}
            <span class="cat">({{ current.category }})</span>
            · {{ current.quantity_sold.toLocaleString() }} 件 · ¥{{ fmtMoneyCN(current.sales, { prefix: '' }) }}
          </span>
        </div>
      </Transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRealtimeStore } from '@/stores/realtimeStore'
import { api } from '@/services/api'
import { fmtMoneyCN } from '@/utils/constants'
import AppIcon from '@/components/common/AppIcon.vue'

interface Highlight {
  product_name: string
  category: string
  quantity_sold: number
  sales: number
}

const items = ref<Highlight[]>([])
const index = ref(0)
const paused = ref(false)
const realtime = useRealtimeStore()

const FALLBACK: Highlight = { product_name: '', category: '', quantity_sold: 0, sales: 0 }
const current = computed<Highlight>(() => items.value[index.value] ?? FALLBACK)

async function load(): Promise<void> {
  try {
    const resp = await api.getProductHighlights(7, 10)
    items.value = resp?.data ?? []
    if (index.value >= items.value.length) index.value = 0
  } catch (err) {
    console.error('[HotProductsTicker] load failed:', err)
  }
}

let flipTimer: number | undefined
let pollTimer: number | undefined

onMounted(() => {
  load()
  flipTimer = window.setInterval(() => {
    if (paused.value) return            // hover 时暂停翻页
    if (items.value.length > 1) {
      index.value = (index.value + 1) % items.value.length
    }
  }, 4000)
  pollTimer = window.setInterval(load, 5 * 60 * 1000)
})

onBeforeUnmount(() => {
  if (flipTimer !== undefined) window.clearInterval(flipTimer)
  if (pollTimer !== undefined) window.clearInterval(pollTimer)
})

watch(() => realtime.counters.order, load)
</script>

<style scoped>
.ticker {
  flex: 0 1 360px;
  min-width: 0;
  max-width: 360px;
  height: 36px;
  background: var(--green-50, #f0fdf4);
  border: 1px solid rgba(34, 197, 94, 0.18);
  border-radius: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 10px;
  overflow: hidden;
  cursor: pointer;
  transition: color 0.15s;
}
.ticker:hover .ticker-text {
  color: var(--green-dark);
}
.ticker-label {
  font-size: 11px;
  font-weight: 800;
  color: var(--green-dark);
  flex-shrink: 0;
  padding: 3px 8px;
  border-radius: 5px;
  background: rgba(34, 197, 94, 0.18);
  letter-spacing: 0.5px;
}
.ticker-stage {
  position: relative;
  flex: 1;
  height: 100%;
  overflow: hidden;
  min-width: 0;
}
.ticker-row {
  position: absolute;
  inset: 0;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text1);
  white-space: nowrap;
  min-width: 0;
}
.ticker-text {
  overflow: hidden;
  text-overflow: ellipsis;
}
.cat {
  color: var(--text3);
  font-weight: 500;
}
.flip-enter-active,
.flip-leave-active {
  transition: transform 0.5s ease, opacity 0.5s ease;
}
.flip-enter-from {
  transform: translateY(100%);
  opacity: 0;
}
.flip-enter-to {
  transform: translateY(0);
  opacity: 1;
}
.flip-leave-from {
  transform: translateY(0);
  opacity: 1;
}
.flip-leave-to {
  transform: translateY(-100%);
  opacity: 0;
}
</style>
