<template>
  <div class="fade-in">
    <PageHeader title="销售概览" subtitle="全店铺销售数据汇总分析(近 30 天,含今日)" />

    <div class="kpi-row">
      <KpiCard title="总销售额" :value="fmtMoneyCN(overview.total_sales, { prefix: '' })" prefix="¥" :change="overview.total_sales_change" icon="finance" icon-bg="#dcfce7" />
      <KpiCard title="订单总数" :value="overview.order_count.toLocaleString()" :change="overview.order_count_change" icon="orders" icon-bg="#dbeafe" />
      <KpiCard title="客单价"   :value="fmtMoneyCN(overview.avg_order_value, { prefix: '' })" prefix="¥" icon="barChart" icon-bg="#ede9fe" />
      <KpiCard title="完成订单" :value="overview.completed_order_count.toLocaleString()" icon="refresh" icon-bg="#fef9c3" />
    </div>

    <div class="kpi-row" v-if="!firstLoaded">
      <div style="width:100%; text-align:center; color:#999">加载中...</div>
    </div>

    <div class="grid-6-4 mb16" v-if="firstLoaded">
      <AppCard title="销售额趋势">
        <template #extra>
          <div class="extra-row">
            <span class="extra">近 30 天</span>
            <button class="ico-btn" title="展开详情" @click="openSalesTrendDetail">
              <AppIcon name="maximize" :size="14" color="var(--text2)" />
            </button>
          </div>
        </template>
        <div class="chart-center"><EChartBox :option="trendOpt" :height="220" /></div>
      </AppCard>
      <AppCard title="品类销售占比">
        <template #extra>
          <button class="ico-btn" title="展开详情" @click="openCategoryDetail">
            <AppIcon name="maximize" :size="14" color="var(--text2)" />
          </button>
        </template>
        <div class="chart-center"><EChartBox :option="catOpt" :height="160" /></div>
        <div style="margin-top:12px">
          <LegendItem v-for="(c, i) in categoriesToDisplay" :key="c.category" :color="PAL[i % PAL.length]" :label="c.category" :value="fmtMoneyCN(c.sales)" :pct="categoryPercent(c.sales)" />
        </div>
      </AppCard>
    </div>

    <div class="mb16" v-if="firstLoaded">
      <AppCard title="品类销售额对比" subtitle="按销售额排序">
        <template #extra>
          <button class="ico-btn" title="展开详情" @click="openCategoryDetail">
            <AppIcon name="maximize" :size="14" color="var(--text2)" />
          </button>
        </template>
        <div class="chart-center"><EChartBox :option="categoryBarOpt" :height="280" /></div>
      </AppCard>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { EChartsOption } from 'echarts'
import PageHeader from '@/components/common/PageHeader.vue'
import KpiCard    from '@/components/common/KpiCard.vue'
import AppCard    from '@/components/common/AppCard.vue'
import EChartBox  from '@/components/common/EChartBox.vue'
import LegendItem from '@/components/common/LegendItem.vue'
import { CHART_PALETTE as PAL, TOOLTIP_BASE, AXIS_GRID, xName, yName, fmtMoneyCN } from '@/utils/constants'
import { api } from '@/services/api'
import { useDebouncedReload } from '@/composables/useEventStream'
import { useChartDetail } from '@/composables/useChartDetail'
import AppIcon from '@/components/common/AppIcon.vue'
import type { TableColumn } from '@/types'

const firstLoaded = ref(false)   // 首次加载完成前显示 spinner;之后 SSE 刷新不再切换 v-if,实现无感更新
const RANGE = '30' as const  // 销售概览所有图表统一近 30 天

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

const trendDays = computed(() => trendChartData.value.map(d => d.date))
const trendSales = computed(() => trendChartData.value.map(d => d.sales))

const categoriesToDisplay = computed(() => {
  return categoryData.value.slice(0, 6)
})

const categoryPieData = computed(() => {
  return categoryData.value.map(c => ({
    name: c.category,
    value: c.sales,
  }))
})

function categoryPercent(sales: number): number {
  const total = categoryData.value.reduce((sum, c) => sum + c.sales, 0)
  return total > 0 ? Math.round((sales / total) * 100) : 0
}

const trendOpt = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis', ...TOOLTIP_BASE, formatter: (p: unknown) => { const params = p as { value: number }[]; return params[0] ? fmtMoneyCN(params[0].value) : '' } },
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
      formatter: (val: string) => val.length >= 10 ? val.slice(5) : val,
    },
  },
  yAxis: {
    type: 'value',
    ...yName('销售额 (¥)'),
    splitLine: { lineStyle: { color: '#f0f4f1' } },
    axisLabel: { formatter: (v: number) => fmtMoneyCN(v, { wanDecimals: 0 }) },
  },
  series: [{ type: 'line', data: trendSales.value, smooth: true, lineStyle: { color: '#52b788', width: 2.5 }, areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(82,183,136,.15)' }, { offset: 1, color: 'rgba(82,183,136,0)' }] } }, symbol: 'none' }],
}))

const catOpt = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'item', ...TOOLTIP_BASE, formatter: (p: unknown) => { const d = p as any; return d ? `${d.name}: ${fmtMoneyCN(d.value)} (${d.percent}%)` : '' } },
  series: [{
    type: 'pie',
    radius: ['45%', '70%'],
    center: ['50%', '50%'],
    avoidLabelOverlap: true,
    data: categoryPieData.value.map((c, i) => ({ name: c.name, value: c.value, itemStyle: { color: PAL[i % PAL.length] } })),
    label: { show: true, formatter: '{b}\n{d}%', fontSize: 11, fontWeight: 700, color: 'inherit' },
    labelLine: { show: true, length: 6, length2: 6, lineStyle: { color: 'inherit' } },
    emphasis: { scale: true, scaleSize: 6, label: { fontSize: 13 } },
  }],
}))

// 品类销售额对比 (替换原本与"销售额趋势"重复的横向 bar)
const categoryBarOpt = computed<EChartsOption>(() => {
  const items = [...categoryData.value].sort((a, b) => b.sales - a.sales)
  return {
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'shadow' }, ...TOOLTIP_BASE,
      formatter: (p: unknown) => { const params = p as any[]; return params?.[0] ? `${params[0].name}: ${fmtMoneyCN(params[0].value)}` : '' },
    },
    grid: AXIS_GRID,
    xAxis: {
      type: 'value',
      ...xName('销售额 (¥)'),
      axisLabel: { formatter: (v: number) => fmtMoneyCN(v, { wanDecimals: 0 }) },
      splitLine: { lineStyle: { color: '#f0f4f1' } },
    },
    yAxis: {
      type: 'category',
      ...yName('品类'),
      data: items.map(c => c.category),
      axisLine: { show: false }, axisTick: { show: false },
      axisLabel: { fontSize: 12, fontWeight: 700 },
    },
    series: [{
      type: 'bar',
      data: items.map(c => c.sales),
      itemStyle: { color: 'rgba(82,183,136,0.85)', borderRadius: [0, 4, 4, 0] },
      barMaxWidth: 18,
      label: {
        show: true, position: 'right',
        formatter: (p: any) => fmtMoneyCN(p.value),
        fontSize: 11, color: 'var(--text2)',
      },
    }],
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
    trendChartData.value = (trendResp as any).data || []
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

// order/finance:销售 KPI / 趋势;customer:客户类型分布;product:品类变更影响 by-category
useDebouncedReload(['order', 'finance', 'customer', 'product'], loadData)

const { open } = useChartDetail()

function buildSalesTrendOpt(rows: { date: string; sales: number; order_count: number }[]): EChartsOption {
  const labels = rows.map(r => r.date.slice(5))
  return {
    tooltip: { trigger: 'axis', ...TOOLTIP_BASE },
    legend: { top: 0, data: ['销售额', '订单数'] },
    grid: { ...AXIS_GRID, top: 60 },
    xAxis: { type: 'category', ...xName('日期'), data: labels, axisLine:{show:false}, axisTick:{show:false}, axisLabel:{interval:Math.max(1,Math.floor(labels.length/12))} },
    yAxis: [
      { type: 'value', ...yName('销售额 (¥)'), splitLine:{lineStyle:{color:'#f0f4f1'}}, axisLabel:{formatter:(v:number)=>fmtMoneyCN(v, { wanDecimals: 0 })} },
      { type: 'value', ...yName('订单数 (单)'), nameLocation:'end' as const, splitLine:{show:false} },
    ],
    series: [
      { name:'销售额', type:'line', data: rows.map(r=>r.sales), smooth:true, lineStyle:{color:'#52b788',width:2.5}, areaStyle:{color:'rgba(82,183,136,.08)'}, symbol:'none' },
      { name:'订单数', type:'bar', yAxisIndex:1, data: rows.map(r=>r.order_count), itemStyle:{color:'rgba(99,102,241,.5)'}, barMaxWidth:10 },
    ],
  }
}

function openSalesTrendDetail() {
  open({
    title: '销售额趋势 · 近 30 天',
    subtitle: '日级销售额与订单数(含今日)',
    load: async () => {
      const r = await api.getSalesTrend(30)
      const rows = (r.data ?? []) as { date: string; sales: number; order_count: number; avg_order_value: number }[]
      const cols: TableColumn[] = [
        { key:'date', title:'日期' },
        { key:'sales', title:'销售额', align:'right', render:(v)=>`¥${(v as number).toLocaleString(undefined,{maximumFractionDigits:2})}` },
        { key:'order_count', title:'订单数', align:'right' },
        { key:'avg_order_value', title:'客单价', align:'right', render:(v)=>`¥${(v as number).toFixed(2)}` },
      ]
      // 图表保持 ASC(左→右=过去→今天),表格按日期 DESC(今天在最上)
      const tableRows = [...rows].reverse()
      return { chartOption: buildSalesTrendOpt(rows), columns: cols, rows: tableRows as unknown as Record<string,unknown>[] }
    },
  })
}

function openCategoryDetail() {
  open({
    title: '品类销售占比 · 近 90 天',
    load: async () => {
      const r = await api.getSalesByCategory('90')
      const data = (r?.data ?? []) as { category: string; sales: number; quantity: number; order_count: number; avg_price: number }[]
      const total = data.reduce((a,c)=>a+c.sales,0) || 1
      const chartOption: EChartsOption = {
        tooltip: { trigger:'item', ...TOOLTIP_BASE, formatter:(p:any)=>`${p.name}: ${fmtMoneyCN(p.value)} (${p.percent}%)` },
        legend: { top: 0 },
        series: [{ type:'pie', radius:['40%','70%'], data: data.map((c,i)=>({ name:c.category, value:c.sales, itemStyle:{color:PAL[i % PAL.length]} })), label:{show:true, formatter:'{b}\n{d}%'} }],
      }
      const cols: TableColumn[] = [
        { key:'category', title:'品类' },
        { key:'sales', title:'销售额', align:'right', render:(v)=>`¥${(v as number).toLocaleString(undefined,{maximumFractionDigits:0})}` },
        { key:'quantity', title:'销售件数', align:'right', render:(v)=>(v as number).toLocaleString() },
        { key:'order_count', title:'订单数', align:'right' },
        { key:'avg_price', title:'均价', align:'right', render:(v)=>`¥${(v as number).toFixed(2)}` },
        { key:'pct', title:'占比', align:'right', render:(_,row)=>`${(((row as any).sales/total)*100).toFixed(1)}%` },
      ]
      return { chartOption, columns: cols, rows: data as unknown as Record<string,unknown>[] }
    },
  })
}

</script>

<style scoped>
.grid-6-4 { display:grid; grid-template-columns:1fr 340px; gap:16px; }
.extra    { font-size:12px; color:var(--text3); }
.extra-row{ display:inline-flex; align-items:center; gap:8px; }
/* 让 AppCard body 撑满卡片可用高度,使 .chart-center 的垂直居中生效 */
:deep(.card)      { height:100%; display:flex; flex-direction:column; }
:deep(.card-body) { flex:1; min-height:0; }
</style>
