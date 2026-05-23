<template>
  <div class="fade-in">
    <PageHeader
      title="财务概览"
      subtitle="近90天收支汇总与财务流水（仅管理员可见）"
    >
      <template #actions>
        <AppBadge label="仅管理员" color="red" size="md" />
      </template>
    </PageHeader>

    <div class="kpi-row">
      <KpiCard
        title="总收入"
        :value="fmtMoneyCN(totalRev, { prefix: '' })"
        prefix="¥"
        icon="trendUp"
        icon-bg="#dcfce7"
      />
      <KpiCard
        title="总支出"
        :value="fmtMoneyCN(totalExp, { prefix: '' })"
        prefix="¥"
        icon="trendDown"
        icon-bg="#fee2e2"
      />
      <KpiCard
        title="净利润"
        :value="fmtMoneyCN(netProfit, { prefix: '' })"
        prefix="¥"
        icon="finance"
        icon-bg="#dbeafe"
      />
      <KpiCard
        title="毛利率"
        :value="grossMargin"
        suffix="%"
        icon="barChart"
        icon-bg="#ede9fe"
      />
    </div>
    <div class="grid-6-4 mb16">
      <AppCard
        title="收支趋势对比"
        subtitle="近30天收入与支出(含今日)"
      >
        <template #extra>
          <button class="ico-btn" title="展开详情" @click="openTrendDetail">
            <AppIcon name="maximize" :size="14" color="var(--text2)" />
          </button>
        </template>
        <EChartBox :option="trendOpt" :height="230" />
      </AppCard>

      <AppCard title="支出构成">
        <template #extra>
          <button class="ico-btn" title="展开详情" @click="openExpenseDetail">
            <AppIcon name="maximize" :size="14" color="var(--text2)" />
          </button>
        </template>
        <EChartBox :option="expOpt" :height="160" />
        <div style="margin-top: 12px">
          <LegendItem
            v-for="e in expItems"
            :key="e.label"
            :color="e.color"
            :label="e.label"
            :value="e.value"
            :pct="e.pct"
          />
        </div>
        <div class="profit-box">
          <div class="profit-label">净利润总计</div>
          <div class="profit-value">{{ fmtMoneyCN(netProfit) }}</div>
          <div class="profit-rate">毛利率 {{ grossMargin }}%</div>
        </div>
      </AppCard>
    </div>
    <AppCard
      title="财务流水明细"
      subtitle="所有收支记录 · 滚动加载"
    >
      <template #extra>
        <ThemedSelect
          v-model="selectedDate"
          :options="dateOpts"
          :min-width="160"
        />
      </template>
      <InfiniteTable
        :columns="cols"
        :loader="loadRecordsPage"
        :reset-key="selectedDate"
        :page-size="50"
        trigger-selector=".kpi-row"
      />
    </AppCard>
  </div>
</template>

<script setup lang="ts">
/* 财务分析页面。 */
import { computed, h, onMounted, ref } from 'vue'
import type { EChartsOption } from 'echarts'
import AppBadge from '@/components/common/AppBadge.vue'
import AppCard from '@/components/common/AppCard.vue'
import AppIcon from '@/components/common/AppIcon.vue'
import EChartBox from '@/components/common/EChartBox.vue'
import InfiniteTable from '@/components/common/InfiniteTable.vue'
import KpiCard from '@/components/common/KpiCard.vue'
import LegendItem from '@/components/common/LegendItem.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import ThemedSelect from '@/components/common/ThemedSelect.vue'
import { useChartDetail } from '@/composables/useChartDetail'
import { useDebouncedReload } from '@/composables/useEventStream'
import { api } from '@/services/api'
import type { FinanceRecord, TableColumn } from '@/types'
import {
  AXIS_GRID,
  FIN_CATEGORY_ZH,
  FIN_TYPE_ZH,
  TOOLTIP_BASE,
  fmtDateTime,
  fmtMoneyCN,
  xName,
  yName,
} from '@/utils/constants'

const PAL_EXP = [
  '#52b788',
  '#74c69d',
  '#b7e4c7',
  '#40916c',
  '#95d5b2',
]

function tooltipSeriesParams(payload: unknown): Array<{ seriesName: string; value: number }> {
  if (!Array.isArray(payload)) {
    return []
  }

  return payload.map((item) => ({
    seriesName: String((item as { seriesName?: unknown }).seriesName ?? ''),
    value:
      typeof (item as { value?: unknown }).value === 'number'
        ? ((item as { value?: number }).value ?? 0)
        : 0,
  }))
}

function tooltipItemName(payload: unknown): string {
  const name = (payload as { name?: unknown })?.name
  return typeof name === 'string' ? name : ''
}

function tooltipItemValue(payload: unknown): number {
  const value = (payload as { value?: unknown })?.value
  return typeof value === 'number' && Number.isFinite(value) ? value : 0
}

function tooltipItemPercent(payload: unknown): number {
  const percent = (payload as { percent?: unknown })?.percent
  return typeof percent === 'number' && Number.isFinite(percent) ? percent : 0
}

const totalRev = ref(0)
const totalExp = ref(0)
const netProfit = computed(() => totalRev.value - totalExp.value)
const grossMargin = computed(() =>
  totalRev.value > 0
    ? ((netProfit.value / totalRev.value) * 100).toFixed(1)
    : '0.0'
)

const trendData = ref<{ date: string; income: number; expense: number }[]>([])
const expBreakdown = ref<{ category: string; amount: number; percentage: number }[]>([])

const selectedDate = ref('all')
const dateOpts = computed(() => {
  const out: { label: string; value: string }[] = [
    { label: '全部日期', value: 'all' },
  ]
  for (let i = 0; i < 30; i++) {
    const d = new Date(Date.now() - i * 86400 * 1000)
    const iso = d.toISOString().slice(0, 10)
    out.push({
      label: i === 0 ? `今天 (${iso.slice(5)})` : iso.slice(5),
      value: iso,
    })
  }
  return out
})

async function loadRecordsPage(page: number, pageSize: number) {
  const date = selectedDate.value === 'all' ? undefined : selectedDate.value
  const resp = await api.getFinanceRecords(
    page,
    pageSize,
    undefined,
    undefined,
    date
  )
  const list: FinanceRecord[] = resp?.data ?? []
  const data = list.map(r => ({
    id: r.id,
    type: FIN_TYPE_ZH[r.type] ?? r.type,
    category: FIN_CATEGORY_ZH[r.category] ?? r.category,
    amount: r.amount,
    orderId: r.order_no ?? '—',
    time: fmtDateTime(r.recorded_at),
  }))
  return {
    data: data as unknown as Record<string, unknown>[],
    total: resp?.pagination?.total ?? 0,
  }
}

const expItems = computed(() =>
  expBreakdown.value.map((e, i) => ({
    label: FIN_CATEGORY_ZH[e.category] ?? e.category,
    color: PAL_EXP[i % PAL_EXP.length],
    value: fmtMoneyCN(e.amount),
    pct: Math.round(e.percentage),
  }))
)

async function loadData() {
  try {
    const [kpi, trend, expense] = await Promise.all([
      api.getFinanceKPI('90'),
      api.getFinanceTrend(30),
      api.getExpenseBreakdown('90'),
    ])

    totalRev.value = kpi?.total_income ?? 0
    totalExp.value = kpi?.total_expense ?? 0
    trendData.value = trend?.data ?? []
    expBreakdown.value = expense?.data ?? []
  } catch (e) {
    console.error('[FinanceView] load failed', e)
  }
}

onMounted(loadData)
useDebouncedReload(['finance', 'order', 'refund'], loadData)

const { open } = useChartDetail()

function openTrendDetail() {
  open({
    title: '收支趋势对比 · 近 30 天',
    load: async () => {
      const r = await api.getFinanceTrend(30)
      const rows = (r?.data ?? []) as {
        date: string
        income: number
        expense: number
        profit: number
      }[]
      const labels = rows.map(d => d.date.slice(5))
      const chartOption: EChartsOption = {
        tooltip: {
          trigger: 'axis',
          ...TOOLTIP_BASE,
          formatter: (payload: unknown) =>
            tooltipSeriesParams(payload)
              .map((item) => `${item.seriesName}: ${fmtMoneyCN(item.value, { wanDecimals: 2 })}`)
              .join('<br>'),
        },
        legend: { top: 0, data: ['收入', '支出', '净利润'] },
        grid: { ...AXIS_GRID, top: 60 },
        xAxis: {
          type: 'category',
          ...xName('日期'),
          data: labels,
          axisLabel: { interval: Math.max(1, Math.floor(labels.length / 12)) },
        },
        yAxis: {
          type: 'value',
          ...yName('金额 (¥)'),
          splitLine: { lineStyle: { color: '#f0f4f1' } },
          axisLabel: { formatter: (v: number) => fmtMoneyCN(v, { wanDecimals: 0 }) },
        },
        series: [
          {
            name: '收入',
            type: 'line',
            data: rows.map(d => d.income),
            smooth: true,
            lineStyle: { color: '#52b788', width: 2.5 },
            areaStyle: { color: 'rgba(82,183,136,.08)' },
            symbol: 'none',
          },
          {
            name: '支出',
            type: 'line',
            data: rows.map(d => d.expense),
            smooth: true,
            lineStyle: { color: '#ef4444', width: 2.5 },
            areaStyle: { color: 'rgba(239,68,68,.06)' },
            symbol: 'none',
          },
          {
            name: '净利润',
            type: 'line',
            data: rows.map(d => d.profit),
            smooth: true,
            lineStyle: { color: '#6366f1', width: 2 },
            symbol: 'none',
          },
        ],
      }
      const cols: TableColumn[] = [
        { key: 'date', title: '日期' },
        {
          key: 'income',
          title: '收入',
          align: 'right',
          render: (v) =>
            `¥${(v as number).toLocaleString(undefined, { maximumFractionDigits: 0 })}`,
        },
        {
          key: 'expense',
          title: '支出',
          align: 'right',
          render: (v) =>
            `¥${(v as number).toLocaleString(undefined, { maximumFractionDigits: 0 })}`,
        },
        {
          key: 'profit',
          title: '净利润',
          align: 'right',
          render: (v) =>
            `¥${(v as number).toLocaleString(undefined, { maximumFractionDigits: 0 })}`,
        },
      ]
      return { chartOption, columns: cols, rows: rows as unknown as Record<string, unknown>[] }
    },
  })
}

function openExpenseDetail() {
  open({
    title: '支出构成 · 近 90 天明细',
    subtitle: '按类目聚合 + 支出类财务流水列表',
    load: async () => {
      const [breakdown, records] = await Promise.all([
        api.getExpenseBreakdown('90'),
        api.getFinanceRecords(1, 100, 'expense'),
      ])
      const items = (breakdown?.data ?? []) as {
        category: string
        amount: number
        percentage: number
      }[]
      const localPal = ['#52b788', '#74c69d', '#b7e4c7', '#40916c', '#95d5b2']
      const chartOption: EChartsOption = {
        tooltip: {
          trigger: 'item',
          ...TOOLTIP_BASE,
          formatter: (payload: unknown) =>
            `${tooltipItemName(payload)}: ${fmtMoneyCN(tooltipItemValue(payload))} (${tooltipItemPercent(payload)}%)`,
        },
        legend: { top: 0 },
        series: [
          {
            type: 'pie',
            radius: ['40%', '70%'],
            data: items.map((e, i) => ({
              name: FIN_CATEGORY_ZH[e.category] ?? e.category,
              value: e.amount,
              itemStyle: { color: localPal[i % localPal.length] },
            })),
            label: { show: true, formatter: '{b}\n{d}%' },
          },
        ],
      }
      const list = (records?.data ?? []) as {
        id: number
        type: string
        category: string
        amount: number
        order_no: string | null
        recorded_at: string | null
      }[]
      const rows = list.map(r => ({
        category: FIN_CATEGORY_ZH[r.category] ?? r.category,
        amount: r.amount,
        order_no: r.order_no ?? '—',
        recorded_at: r.recorded_at
          ? r.recorded_at.replace('T', ' ').slice(0, 16)
          : '—',
      }))
      const cols: TableColumn[] = [
        { key: 'category', title: '类目' },
        {
          key: 'amount',
          title: '金额',
          align: 'right',
          render: (v) =>
            `¥${(v as number).toLocaleString(undefined, { maximumFractionDigits: 2 })}`,
        },
        { key: 'order_no', title: '关联订单', render: (v) => String(v) },
        { key: 'recorded_at', title: '记录时间' },
      ]
      return { chartOption, columns: cols, rows: rows as unknown as Record<string, unknown>[] }
    },
  })
}

const trendOpt = computed<EChartsOption>(() => {
  const labels = trendData.value.map(d => {
    const [, m, day] = d.date.split('-')
    return `${parseInt(m)}/${parseInt(day)}`
  })
  return {
    tooltip: {
      trigger: 'axis',
      ...TOOLTIP_BASE,
      formatter: (payload: unknown) =>
        tooltipSeriesParams(payload)
          .map((item) => `${item.seriesName}: ${fmtMoneyCN(item.value, { wanDecimals: 2 })}`)
          .join('<br>'),
    },
    legend: { top: 0, data: ['收入', '支出'], textStyle: { fontSize: 11 } },
    grid: { ...AXIS_GRID, top: 60 },
    xAxis: {
      type: 'category',
      ...xName('日期'),
      data: labels,
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { interval: Math.max(1, Math.floor(labels.length / 8)) },
    },
    yAxis: {
      type: 'value',
      ...yName('金额 (¥)'),
      splitLine: { lineStyle: { color: '#f0f4f1' } },
      axisLabel: { formatter: (v: number) => fmtMoneyCN(v, { wanDecimals: 0 }) },
    },
    series: [
      {
        name: '收入',
        type: 'line',
        data: trendData.value.map(d => d.income),
        smooth: true,
        lineStyle: { color: '#52b788', width: 2.5 },
        areaStyle: { color: 'rgba(82,183,136,.07)' },
        symbol: 'circle',
        symbolSize: 4,
        itemStyle: { color: '#52b788' },
      },
      {
        name: '支出',
        type: 'line',
        data: trendData.value.map(d => d.expense),
        smooth: true,
        lineStyle: { color: '#ef4444', width: 2.5 },
        areaStyle: { color: 'rgba(239,68,68,.05)' },
        symbol: 'circle',
        symbolSize: 4,
        itemStyle: { color: '#ef4444' },
      },
    ],
  }
})

const expOpt = computed<EChartsOption>(() => ({
  tooltip: {
    trigger: 'item',
    formatter: (payload: unknown) =>
      `${tooltipItemName(payload)}: ${tooltipItemValue(payload).toFixed(1)}% (${tooltipItemPercent(payload)}%)`,
  },
  series: [
    {
      type: 'pie',
      radius: ['50%', '72%'],
      avoidLabelOverlap: true,
      data: expBreakdown.value.map((e, i) => ({
        name: FIN_CATEGORY_ZH[e.category] ?? e.category,
        value: e.percentage,
        itemStyle: { color: PAL_EXP[i % PAL_EXP.length] },
      })),
      label: {
        show: true,
        formatter: '{b}\n{d}%',
        fontSize: 11,
        fontWeight: 700,
        color: 'inherit',
      },
      labelLine: { show: true, length: 6, length2: 6, lineStyle: { color: 'inherit' } },
      emphasis: { scale: true, scaleSize: 6, label: { fontSize: 13 } },
    },
  ],
}))

const cols: TableColumn[] = [
  {
    key: 'type',
    title: '类型',
    render: (v) =>
      h(
        'span',
        {
          style: {
            display: 'inline-flex',
            alignItems: 'center',
            padding: '2px 9px',
            borderRadius: '99px',
            fontSize: '12px',
            fontWeight: 700,
            background: v === '收入' ? '#dcfce7' : '#fee2e2',
            color: v === '收入' ? '#15803d' : '#dc2626',
          },
        },
        String(v),
      ),
  },
  { key: 'category', title: '类目' },
  {
    key: 'amount',
    title: '金额',
    align: 'right',
    render: (v, row) => {
      const r = row as { type: string }
      const isIncome = r.type === '收入'
      return h(
        'span',
        { style: { fontWeight: 800, color: isIncome ? '#16a34a' : '#dc2626' } },
        `${isIncome ? '+' : '-'}¥${(v as number).toLocaleString(undefined, {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })}`,
      )
    },
  },
  {
    key: 'orderId',
    title: '关联订单号',
    render: (v) =>
      h(
        'span',
        { style: { fontFamily: 'monospace', fontSize: '12px', color: 'var(--text2)' } },
        String(v),
      ),
  },
  {
    key: 'time',
    title: '记录时间',
    render: (v) =>
      h(
        'span',
        { style: { fontSize: '12px', color: 'var(--text2)' } },
        String(v),
      ),
  },
]
</script>

<style scoped>
.grid-6-4 {
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 16px;
}

.profit-box {
  margin-top: 14px;
  padding: 12px 14px;
  border-radius: 10px;
  background: var(--green-50);
  border: 1px solid var(--green-100);
}

.profit-label {
  font-size: 12px;
  color: var(--text2);
  margin-bottom: 4px;
  font-weight: 700;
}

.profit-value {
  font-size: 22px;
  font-weight: 900;
  color: var(--green-dark);
}

.profit-rate {
  font-size: 12px;
  color: var(--text3);
  margin-top: 2px;
}
</style>
