/* 服务端事件流订阅与刷新逻辑 */

import { onBeforeUnmount, watch } from 'vue'
import { useRealtimeStore, type BusEntity } from '@/stores/realtimeStore'

export type { BusEntity }

export type BusEvent = {
  entity: BusEntity
  action: 'create' | 'delete' | 'update' | 'hello'
  payload: Record<string, unknown>
}

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

  
  const stopWatch = watch(
    () => entities.map((entity) => realtime.counters[entity] ?? 0).join(','),
    () => {
      const now = Date.now()
      const elapsed = now - lastFired

      if (elapsed >= delayMs) {
        
        lastFired = now
        reload()
      } else if (pendingTimer === null) {
        
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
