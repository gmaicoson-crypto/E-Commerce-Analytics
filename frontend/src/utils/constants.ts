/* 图表与界面共用常量及格式化方法 */

import type { BadgeColor } from '@/types'

export const CHART_PALETTE: string[] = [
  '#52b788',
  '#74c69d',
  '#b7e4c7',
  '#40916c',
  '#2d6a4f',
  '#95d5b2',
  '#1b4332',
  '#d8f3dc',
]

export const BADGE_MAP: Record<BadgeColor, { bg: string; fg: string }> = {
  green: { bg: '#dcfce7', fg: '#15803d' },
  red: { bg: '#fee2e2', fg: '#dc2626' },
  yellow: { bg: '#fef9c3', fg: '#ca8a04' },
  blue: { bg: '#dbeafe', fg: '#1d4ed8' },
  purple: { bg: '#ede9fe', fg: '#7c3aed' },
  gray: { bg: '#f1f5f0', fg: '#4b5563' },
  orange: { bg: '#ffedd5', fg: '#ea580c' },
}

export const TOOLTIP_BASE = {
  backgroundColor: '#1a2b1e',
  padding: 10,
  borderRadius: 8,
  textStyle: { color: '#fff' },
} as const

const AXIS_NAME_STYLE = {
  fontSize: 12,
  color: 'var(--text2)',
  fontWeight: 700,
} as const

export function xName(name: string) {
  return {
    name,
    nameLocation: 'middle' as const,
    nameGap: 36,
    nameTextStyle: AXIS_NAME_STYLE,
  }
}

export function yName(name: string) {
  return {
    name,
    nameLocation: 'end' as const,
    nameGap: 20,
    nameTextStyle: { ...AXIS_NAME_STYLE, align: 'left' as const },
  }
}

export const AXIS_GRID = {
  left: 14,
  right: 28,
  top: 50,
  bottom: 60,
  containLabel: true,
} as const

export const ORDER_STATUS_ZH: Record<string, string> = {
  pending: '待支付',
  paid: '已支付',
  shipped: '已发货',
  completed: '已完成',
  cancelled: '已取消',
  refunded: '已退款',
}

export const ORDER_STATUS_EN: Record<string, string> = Object.fromEntries(
  Object.entries(ORDER_STATUS_ZH).map(([en, zh]) => [zh, en]),
)

export const NOTIF_TYPE_ZH: Record<string, string> = {
  stock_alert:  '库存预警',
  refund_alert: '大额退款',
  order_alert:  '异常订单',
  sales_alert:  '销售额波动',
}

export const FIN_TYPE_ZH: Record<string, string> = {
  income: '收入',
  expense: '支出',
}

export const FIN_CATEGORY_ZH: Record<string, string> = {
  sales_income: '销售收入',
  product_cost: '商品成本',
  logistics_cost: '物流成本',
  ad_cost: '广告成本',
  refund_out: '退款支出',
}

const pad2 = (n: number) => String(n).padStart(2, '0')

export function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) {
    return '—'
  }

  const d = new Date(iso)

  if (isNaN(d.getTime())) {
    return iso
  }

  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} ${pad2(d.getHours())}:${pad2(d.getMinutes())}`
}

export function fmtMoneyCN(
  value: number | null | undefined,
  opts: { prefix?: string; wanDecimals?: number; smallDecimals?: number } = {},
): string {
  const { prefix = '¥', wanDecimals = 1, smallDecimals = 2 } = opts
  const v = Number(value)

  if (!Number.isFinite(v)) {
    return `${prefix}0`
  }

  if (Math.abs(v) >= 10000) {
    return `${prefix}${(v / 10000).toFixed(wanDecimals)}万`
  }

  return `${prefix}${v.toLocaleString(undefined, { maximumFractionDigits: smallDecimals })}`
}

export function recentDayLabels(days: number): string[] {
  const today = new Date()
  return Array.from({ length: days }, (_, i) => {
    const d = new Date(today)
    d.setDate(today.getDate() - (days - 1 - i))
    return `${d.getMonth() + 1}/${d.getDate()}`
  })
}
