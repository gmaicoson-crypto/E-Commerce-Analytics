/* 图表详情弹窗状态管理 */

import { ref, readonly } from 'vue'
import type { EChartsOption } from 'echarts'
import type { TableColumn } from '@/types'

export type ChartDetailFilterOption = { label: string; value: string }

export type ChartDetailFilter = {
  key: string 
  label: string 
  options: ChartDetailFilterOption[]
  default?: string
}

export type ChartDetailConfig = {
  title: string
  subtitle?: string
  filters?: ChartDetailFilter[] 
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
    open: (config: ChartDetailConfig) => {
      current.value = config
    },
    close: () => {
      current.value = null
    },
  }
}
