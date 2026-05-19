/**
 * 全局图表详情 Modal 状态。
 * 在任意视图中调用 useChartDetail().open(config) 即可弹出大图 + 明细表。
 */
import { ref, readonly } from 'vue'
import type { EChartsOption } from 'echarts'
import type { TableColumn } from '@/types'

export type ChartDetailFilterOption = { label: string; value: string }

export type ChartDetailFilter = {
  key: string                          // 在 selected 中的字段名
  label: string                        // UI 显示文字
  options: ChartDetailFilterOption[]
  default?: string
}

export type ChartDetailConfig = {
  title: string
  subtitle?: string
  filters?: ChartDetailFilter[]        // 可选 —— 弹窗顶部下拉,切换时重新调用 load
  load: (selected: Record<string, string>) => Promise<{
    chartOption: EChartsOption
    columns: TableColumn[]
    rows: Record<string, unknown>[]
  }>
}

const current = ref<ChartDetailConfig | null>(null)

export function useChartDetail() {
  return {
    current: readonly(current),
    open: (cfg: ChartDetailConfig) => { current.value = cfg },
    close: () => { current.value = null },
  }
}
