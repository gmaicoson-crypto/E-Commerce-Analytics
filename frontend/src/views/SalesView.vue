<template>
  <div class="fade-in">
    <PageHeader
      title="销售概览"
      subtitle="全店铺销售数据汇总分析(近 30 天,含今日)"
    />

    <div class="kpi-row">
      <KpiCard
        title="总销售额"
        :value="fmtMoneyCN(overview.total_sales, { prefix: '' })"
        prefix="¥"
        :change="overview.total_sales_change"
        icon="finance"
        icon-bg="#dcfce7"
      />
      <KpiCard
        title="订单总数"
        :value="overview.order_count.toLocaleString()"
        :change="overview.order_count_change"
        icon="orders"
        icon-bg="#dbeafe"
      />
      <KpiCard
        title="客单价"
        :value="fmtMoneyCN(overview.avg_order_value, { prefix: '' })"
        prefix="¥"
        icon="barChart"
        icon-bg="#ede9fe"
      />
      <KpiCard
        title="完成订单"
        :value="overview.completed_order_count.toLocaleString()"
        icon="refresh"
        icon-bg="#fef9c3"
      />
    </div>

    <div v-if="!firstLoaded" class="kpi-row">
      <div class="loading-hint">加载中...</div>
    </div>

    <div v-if="firstLoaded" class="grid-6-4 mb16">
      <AppCard title="销售额趋势">
        <template #extra>
          <div class="extra-row">
            <span class="extra">近 30 天</span>
            <button
              class="ico-btn"
              title="展开详情"
              @click="openSalesTrendDetail"
            >
              <AppIcon name="maximize" :size="14" color="var(--text2)" />
            </button>
          </div>
        </template>

        <div class="chart-center">
          <EChartBox :option="trendOpt" :height="220" />
        </div>
      </AppCard>

      <AppCard title="品类销售占比">
        <template #extra>
          <button
            class="ico-btn"
            title="展开详情"
            @click="openCategoryDetail"
          >
            <AppIcon name="maximize" :size="14" color="var(--text2)" />
          </button>
        </template>

        <div class="chart-center">
          <EChartBox :option="catOpt" :height="160" />
        </div>

        <div class="legend-wrap">
          <LegendItem
            v-for="(category, index) in categoriesToDisplay"
            :key="category.category"
            :color="PAL[index % PAL.length]"
            :label="category.category"
            :value="fmtMoneyCN(category.sales)"
            :pct="categoryPercent(category.sales)"
          />
        </div>
      </AppCard>
    </div>

    <div v-if="firstLoaded" class="mb16">
      <AppCard title="品类销售额对比" subtitle="按销售额排序">
        <template #extra>
          <button
            class="ico-btn"
            title="展开详情"
            @click="openCategoryDetail"
          >
            <AppIcon name="maximize" :size="14" color="var(--text2)" />
          </button>
        </template>

        <div class="chart-center">
          <EChartBox :option="categoryBarOpt" :height="280" />
        </div>
      </AppCard>
    </div>
  </div>
</template>

<script setup lang="ts">
/* 销售概览页面。 */
import type { EChartsOption } from 'echarts'
import { computed, onMounted, ref } from 'vue'
import AppCard from '@/components/common/AppCard.vue'
import AppIcon from '@/components/common/AppIcon.vue'
import EChartBox from '@/components/common/EChartBox.vue'
import KpiCard from '@/components/common/KpiCard.vue'
import LegendItem from '@/components/common/LegendItem.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import { useChartDetail } from '@/composables/useChartDetail'
import { useDebouncedReload } from '@/composables/useEventStream'
import { api } from '@/services/api'
import type { TableColumn } from '@/types'
import {
  AXIS_GRID,
  CHART_PALETTE as PAL,
  TOOLTIP_BASE,
  fmtMoneyCN,
  xName,
  yName,
} from '@/utils/constants'

function tooltipValue(payload: unknown): number {
  const value = (payload as { value?: unknown })?.value
  return typeof value === 'number' && Number.isFinite(value) ? value : 0
}

function tooltipName(payload: unknown): string {
  const name = (payload as { name?: unknown })?.name
  return typeof name === 'string' ? name : ''
}

function tooltipPercent(payload: unknown): number {
  const percent = (payload as { percent?: unknown })?.percent
  return typeof percent === 'number' && Number.isFinite(percent) ? percent : 0
}

function tooltipArray(payload: unknown): Array<{ name: string; value: number }> {
  if (!Array.isArray(payload)) {
    return []
  }

  return payload.map((item) => ({
    name: tooltipName(item),
    value: tooltipValue(item),
  }))
}

const firstLoaded = ref(false)
const RANGE = '30' as const

const overview = ref({
  period: { start: '', end: '' },
  total_sales: 0,
  total_sales_change: 0,
  order_count: 0,
  order_count_change: 0,
  avg_order_value: 0,
  completed_sales: 0,
  completed_order_count: 0,
})

const trendChartData = ref<Array<{ date: string; sales: number; order_count: number }>>([])
const categoryData = ref<Array<{ category: string; sales: number; quantity: number }>>([])

const trendDays = computed(() => trendChartData.value.map((item) => item.date))
const trendSales = computed(() => trendChartData.value.map((item) => item.sales))

const categoriesToDisplay = computed(() => categoryData.value.slice(0, 6))

const categoryPieData = computed(() =>
  categoryData.value.map((item) => ({
    name: item.category,
    value: item.sales,
  })),
)

function categoryPercent(sales: number): number {
  const total = categoryData.value.reduce((sum, item) => sum + item.sales, 0)
  return total > 0 ? Math.round((sales / total) * 100) : 0
}

const trendOpt = computed<EChartsOption>(() => ({
  tooltip: {
    trigger: 'axis',
    ...TOOLTIP_BASE,
    formatter: (payload: unknown) => {
      const params = tooltipArray(payload)
      return params[0] ? fmtMoneyCN(params[0].value) : ''
    },
  },
  grid: AXIS_GRID,
  xAxis: {
    type: 'category',
    ...xName('日期'),
    data: trendDays.value,
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: { show: false },
    axisLabel: {
      interval: Math.max(0, Math.floor(trendDays.value.length / 8)),
      formatter: (value: string) => (value.length >= 10 ? value.slice(5) : value),
    },
  },
  yAxis: {
    type: 'value',
    ...yName('销售额 (¥)'),
    splitLine: {
      lineStyle: { color: '#f0f4f1' },
    },
    axisLabel: {
      formatter: (value: number) => fmtMoneyCN(value, { wanDecimals: 0 }),
    },
  },
  series: [
    {
      type: 'line',
      data: trendSales.value,
      smooth: true,
      lineStyle: {
        color: '#52b788',
        width: 2.5,
      },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(82,183,136,.15)' },
            { offset: 1, color: 'rgba(82,183,136,0)' },
          ],
        },
      },
      symbol: 'none',
    },
  ],
}))

const catOpt = computed<EChartsOption>(() => ({
  tooltip: {
    trigger: 'item',
    ...TOOLTIP_BASE,
    formatter: (payload: unknown) =>
      `${tooltipName(payload)}: ${fmtMoneyCN(tooltipValue(payload))} (${tooltipPercent(payload)}%)`,
  },
  series: [
    {
      type: 'pie',
      radius: ['45%', '70%'],
      center: ['50%', '50%'],
      avoidLabelOverlap: true,
      data: categoryPieData.value.map((item, index) => ({
        name: item.name,
        value: item.value,
        itemStyle: { color: PAL[index % PAL.length] },
      })),
      label: {
        show: true,
        formatter: '{b}\n{d}%',
        fontSize: 11,
        fontWeight: 700,
        color: 'inherit',
      },
      labelLine: {
        show: true,
        length: 6,
        length2: 6,
        lineStyle: { color: 'inherit' },
      },
      emphasis: {
        scale: true,
        scaleSize: 6,
        label: { fontSize: 13 },
      },
    },
  ],
}))

const categoryBarOpt = computed<EChartsOption>(() => {
  const items = [...categoryData.value].sort((a, b) => b.sales - a.sales)

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      ...TOOLTIP_BASE,
      formatter: (payload: unknown) => {
        const params = tooltipArray(payload)
        return params?.[0]
          ? `${params[0].name}: ${fmtMoneyCN(params[0].value)}`
          : ''
      },
    },
    grid: AXIS_GRID,
    xAxis: {
      type: 'value',
      ...xName('销售额 (¥)'),
      axisLabel: {
        formatter: (value: number) => fmtMoneyCN(value, { wanDecimals: 0 }),
      },
      splitLine: {
        lineStyle: { color: '#f0f4f1' },
      },
    },
    yAxis: {
      type: 'category',
      ...yName('品类'),
      data: items.map((item) => item.category),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        fontSize: 12,
        fontWeight: 700,
      },
    },
    series: [
      {
        type: 'bar',
        data: items.map((item) => item.sales),
        itemStyle: {
          color: 'rgba(82,183,136,0.85)',
          borderRadius: [0, 4, 4, 0],
        },
        barMaxWidth: 18,
        label: {
          show: true,
          position: 'right',
          formatter: (payload: unknown) => fmtMoneyCN(tooltipValue(payload)),
          fontSize: 11,
          color: 'var(--text2)',
        },
      },
    ],
  }
})

async function loadData() {
  try {
    const [overviewResp, trendResp, categoryResp] = await Promise.all([
      api.getSalesOverview(RANGE),
      api.getSalesTrend(30),
      api.getSalesByCategory(RANGE),
    ])

    overview.value = overviewResp
    trendChartData.value = (trendResp as { data?: Array<{ date: string; sales: number; order_count: number }> }).data || []
    categoryData.value = categoryResp.data || []
  } catch (error) {
    console.error('Failed to load sales data:', error)
  } finally {
    firstLoaded.value = true
  }
}

onMounted(() => {
  loadData()
})

useDebouncedReload(['order', 'finance', 'customer', 'product'], loadData)

const { open } = useChartDetail()

function buildSalesTrendOpt(
  rows: { date: string; sales: number; order_count: number }[],
): EChartsOption {
  const labels = rows.map((row) => row.date.slice(5))

  return {
    tooltip: {
      trigger: 'axis',
      ...TOOLTIP_BASE,
    },
    legend: {
      top: 0,
      data: ['销售额', '订单数'],
    },
    grid: {
      ...AXIS_GRID,
      top: 60,
    },
    xAxis: {
      type: 'category',
      ...xName('日期'),
      data: labels,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        interval: Math.max(1, Math.floor(labels.length / 12)),
      },
    },
    yAxis: [
      {
        type: 'value',
        ...yName('销售额 (¥)'),
        splitLine: {
          lineStyle: { color: '#f0f4f1' },
        },
        axisLabel: {
          formatter: (value: number) => fmtMoneyCN(value, { wanDecimals: 0 }),
        },
      },
      {
        type: 'value',
        ...yName('订单数 (单)'),
        nameLocation: 'end',
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: '销售额',
        type: 'line',
        data: rows.map((row) => row.sales),
        smooth: true,
        lineStyle: {
          color: '#52b788',
          width: 2.5,
        },
        areaStyle: {
          color: 'rgba(82,183,136,.08)',
        },
        symbol: 'none',
      },
      {
        name: '订单数',
        type: 'bar',
        yAxisIndex: 1,
        data: rows.map((row) => row.order_count),
        itemStyle: {
          color: 'rgba(99,102,241,.5)',
        },
        barMaxWidth: 10,
      },
    ],
  }
}

function openSalesTrendDetail() {
  open({
    title: '销售额趋势 · 近 30 天',
    subtitle: '日级销售额与订单数(含今日)',
    load: async () => {
      const response = await api.getSalesTrend(30)
      const rows = (response.data ?? []) as Array<{
        date: string
        sales: number
        order_count: number
        avg_order_value: number
      }>

      const columns: TableColumn[] = [
        { key: 'date', title: '日期' },
        {
          key: 'sales',
          title: '销售额',
          align: 'right',
          render: (value) =>
            `¥${(value as number).toLocaleString(undefined, {
              maximumFractionDigits: 2,
            })}`,
        },
        { key: 'order_count', title: '订单数', align: 'right' },
        {
          key: 'avg_order_value',
          title: '客单价',
          align: 'right',
          render: (value) => `¥${(value as number).toFixed(2)}`,
        },
      ]

      const tableRows = [...rows].reverse()

      return {
        chartOption: buildSalesTrendOpt(rows),
        columns,
        rows: tableRows as unknown as Record<string, unknown>[],
      }
    },
  })
}

function openCategoryDetail() {
  open({
    title: '品类销售占比 · 近 90 天',
    load: async () => {
      const response = await api.getSalesByCategory('90')
      const data = (response?.data ?? []) as Array<{
        category: string
        sales: number
        quantity: number
        order_count: number
        avg_price: number
      }>

      const total = data.reduce((sum, item) => sum + item.sales, 0) || 1

      const chartOption: EChartsOption = {
        tooltip: {
          trigger: 'item',
          ...TOOLTIP_BASE,
          formatter: (payload: unknown) =>
            `${tooltipName(payload)}: ${fmtMoneyCN(tooltipValue(payload))} (${tooltipPercent(payload)}%)`,
        },
        legend: { top: 0 },
        series: [
          {
            type: 'pie',
            radius: ['40%', '70%'],
            data: data.map((item, index) => ({
              name: item.category,
              value: item.sales,
              itemStyle: { color: PAL[index % PAL.length] },
            })),
            label: {
              show: true,
              formatter: '{b}\n{d}%',
            },
          },
        ],
      }

      const columns: TableColumn[] = [
        { key: 'category', title: '品类' },
        {
          key: 'sales',
          title: '销售额',
          align: 'right',
          render: (value) =>
            `¥${(value as number).toLocaleString(undefined, {
              maximumFractionDigits: 0,
            })}`,
        },
        {
          key: 'quantity',
          title: '销售件数',
          align: 'right',
          render: (value) => (value as number).toLocaleString(),
        },
        { key: 'order_count', title: '订单数', align: 'right' },
        {
          key: 'avg_price',
          title: '均价',
          align: 'right',
          render: (value) => `¥${(value as number).toFixed(2)}`,
        },
        {
          key: 'pct',
          title: '占比',
          align: 'right',
          render: (_, row) =>
            `${((((row as { sales: number }).sales) / total) * 100).toFixed(1)}%`,
        },
      ]

      return {
        chartOption,
        columns,
        rows: data as unknown as Record<string, unknown>[],
      }
    },
  })
}
</script>

<style scoped>
.loading-hint {
  width: 100%;
  color: #999;
  text-align: center;
}

.legend-wrap {
  margin-top: 12px;
}

.grid-6-4 {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 16px;
}

.extra {
  font-size: 12px;
  color: var(--text3);
}

.extra-row {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

:deep(.card) {
  display: flex;
  flex-direction: column;
  height: 100%;
}

:deep(.card-body) {
  flex: 1;
  min-height: 0;
}
</style>
