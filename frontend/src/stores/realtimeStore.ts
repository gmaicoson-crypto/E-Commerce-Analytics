/**
 * 全局实时事件总线 —— 全应用唯一 EventSource,常驻整个登录态。
 *
 * 视图通过 useDebouncedReload(['order','finance'], reload) watch 对应 entity 的计数器变化,
 * 一旦后端 publish 该类型事件,store 的 counters[entity]++,所有 watcher 触发 reload。
 *
 * 优点:
 *   - 单连接,无视图切换断开重连的中间窗口丢事件
 *   - 计数器 watcher 是 Vue 原生响应式,精准,不需要 EventListener 派发
 */
import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import { API_BASE } from '@/services/api'

export type BusEntity =
  | 'order' | 'product' | 'customer' | 'notification' | 'finance' | 'refund' | 'system'

const INITIAL_COUNTERS: Record<BusEntity, number> = {
  order: 0, product: 0, customer: 0, notification: 0, finance: 0, refund: 0, system: 0,
}

export const useRealtimeStore = defineStore('realtime', () => {
  const counters = reactive<Record<BusEntity, number>>({ ...INITIAL_COUNTERS })
  const connected = ref(false)
  let es: EventSource | null = null
  let reconnectTimer: number | null = null

  function bump(entity: string): void {
    if (entity in counters) {
      counters[entity as BusEntity] = (counters[entity as BusEntity] ?? 0) + 1
    }
  }

  function connect(): void {
    if (es) return
    const token = localStorage.getItem('token')
    if (!token) return

    es = new EventSource(`${API_BASE}/sse/events?token=${encodeURIComponent(token)}`)

    es.onopen = () => { connected.value = true }

    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data)
        if (!data || data.action === 'hello') return
        if (data.entity) bump(data.entity as string)
      } catch (err) {
        console.error('[realtime] parse error', err)
      }
    }

    es.onerror = () => {
      connected.value = false
      es?.close()
      es = null
      if (reconnectTimer === null) {
        reconnectTimer = window.setTimeout(() => {
          reconnectTimer = null
          connect()
        }, 3000)
      }
    }
  }

  function disconnect(): void {
    if (reconnectTimer !== null) {
      window.clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    es?.close()
    es = null
    connected.value = false
  }

  return { counters, connected, connect, disconnect, bump }
})
