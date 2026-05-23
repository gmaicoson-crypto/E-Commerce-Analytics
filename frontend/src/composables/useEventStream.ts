/**
 * 视图层订阅工具 —— 通过 realtimeStore 的计数器响应实时事件,throttle 后调 reload。
 *
 * API 与之前一致(`useDebouncedReload(entities, reload, delayMs)`),
 * 但内部不再每个 view 开 EventSource,改 watch 全局 store 的 entity 计数器变化。
 */
import { onBeforeUnmount, watch } from 'vue'
import { useRealtimeStore, type BusEntity } from '@/stores/realtimeStore'

export type { BusEntity }

export type BusEvent = {
  entity: BusEntity
  action: 'create' | 'delete' | 'update' | 'hello'
  payload: Record<string, unknown>
}

/**
 * 当任一 entity 的实时计数器变化时,throttle(leading + trailing)触发 reload()。
 *
 * 为何不用 debounce:自动化高频跑(2000 events/min ≈ 33/s)时,
 * debounce 计时器持续被清,直到事件流停下来才触发 → 看起来"只有停脚本才刷新"。
 *
 * throttle 模式:第一个事件立即触发,delayMs 窗口内累积的事件合并成 1 次 trailing reload。
 * delayMs 默认 1000ms —— 高频场景下每秒最多 1 次 reload,既保证视觉"无感刷新",
 * 又不会让 3-4 个 API 并发请求把后端压垮。
 */
export function useDebouncedReload(
  entities: BusEntity[],
  reload: () => void,
  delayMs = 1000,
): void {
  const realtime = useRealtimeStore()
  let lastFired = 0
  let pendingTimer: number | null = null

  function clearPendingTimer(): void {
    if (pendingTimer !== null) {
      window.clearTimeout(pendingTimer)
      pendingTimer = null
    }
  }

  // 把多个 entity 计数器合并成一个稳定字符串,变化即触发
  const stopWatch = watch(
    () => entities.map((entity) => realtime.counters[entity] ?? 0).join(','),
    () => {
      const now = Date.now()
      const elapsed = now - lastFired

      if (elapsed >= delayMs) {
        // 距上次刷新足够久 → 立即触发(leading edge)
        lastFired = now
        reload()
      } else if (pendingTimer === null) {
        // 当前窗口内还有事件 → 安排一次 trailing reload,窗口结束时拿最新数据
        pendingTimer = window.setTimeout(() => {
          pendingTimer = null
          lastFired = Date.now()
          reload()
        }, delayMs - elapsed)
      }
    },
  )

  onBeforeUnmount(() => {
    clearPendingTimer()
    stopWatch()
  })
}
