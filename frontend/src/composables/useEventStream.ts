/**
 * 视图层订阅工具 —— 通过 realtimeStore 的计数器响应实时事件,debounce 后调 reload。
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
 * 当任一 entity 的实时计数器变化时,debounce 后触发 reload()。
 * 多个事件在 delayMs 内合并成一次 reload。
 */
export function useDebouncedReload(
  entities: BusEntity[],
  reload: () => void,
  delayMs = 200,   // 调短 → 自动化 1 事件/秒 时,KPI 计时器感更强
): void {
  const realtime = useRealtimeStore()
  let timer: number | null = null
  const clear = () => {
    if (timer !== null) {
      window.clearTimeout(timer)
      timer = null
    }
  }
  // 把多个 entity 计数器合并成一个稳定字符串,变化即触发
  const stopWatch = watch(
    () => entities.map((e) => realtime.counters[e] ?? 0).join(','),
    () => {
      clear()
      timer = window.setTimeout(() => {
        timer = null
        reload()
      }, delayMs)
    },
  )
  onBeforeUnmount(() => {
    clear()
    stopWatch()
  })
}
