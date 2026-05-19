<template>
  <div class="fade-in">
    <PageHeader title="订单分析" subtitle="订单状态、趋势及明细管理" />
    <div class="kpi-grid mb16">
      <KpiCard title="总订单数"     :value="overview.total_orders?.toLocaleString() ?? '—'"     icon="orders"      icon-bg="#dcfce7" />
      <KpiCard title="平均订单金额" :value="overview.avg_order_value?.toFixed(2) ?? '—'" prefix="¥" icon="finance" icon-bg="#ede9fe" />
      <KpiCard
        title="待支付" icon="orders" icon-bg="#fef9c3"
        :value="overview.pending_count?.toLocaleString() ?? '—'"
        :sub-value="`¥${fmtMoneyCN(overview.pending_amount ?? 0, { prefix: '' })}`" sub-label="金额"
      />
      <KpiCard
        title="已支付" icon="orders" icon-bg="#dbeafe"
        :value="overview.paid_count?.toLocaleString() ?? '—'"
        :sub-value="`¥${fmtMoneyCN(overview.paid_amount ?? 0, { prefix: '' })}`" sub-label="金额"
      />
      <KpiCard
        title="已发货" icon="orders" icon-bg="#ede9fe"
        :value="overview.shipped_count?.toLocaleString() ?? '—'"
        :sub-value="`¥${fmtMoneyCN(overview.shipped_amount ?? 0, { prefix: '' })}`" sub-label="金额"
      />
      <KpiCard
        title="已完成" icon="checkCircle" icon-bg="#dcfce7"
        :value="overview.completed_count?.toLocaleString() ?? '—'"
        :sub-value="`¥${fmtMoneyCN(overview.completed_amount ?? 0, { prefix: '' })}`" sub-label="金额"
      />
      <KpiCard
        title="已取消" icon="orders" icon-bg="#f3f4f6"
        :value="overview.cancelled_count?.toLocaleString() ?? '—'"
        :sub-value="`¥${fmtMoneyCN(overview.cancelled_amount ?? 0, { prefix: '' })}`" sub-label="金额"
      />
      <KpiCard
        title="已退款" icon="refresh" icon-bg="#fee2e2"
        :value="overview.refunded_count?.toLocaleString() ?? '—'"
        :sub-value="`¥${fmtMoneyCN(overview.refunded_amount ?? 0, { prefix: '' })}`" sub-label="金额"
      />
    </div>
    <div class="grid-side-main mb16">
      <AppCard title="订单状态分布">
        <template #extra>
          <button class="ico-btn" title="展开详情" @click="openStatusDetail">
            <AppIcon name="maximize" :size="14" color="var(--text2)" />
          </button>
        </template>
        <EChartBox :option="statusOpt" :height="160" />
        <div style="margin-top:12px">
          <LegendItem v-for="s in statusDist" :key="s.name" :color="COLOR_MAP[s.name]" :label="s.name" :value="s.count.toLocaleString()" :pct="s.pct" />
        </div>
      </AppCard>
      <AppCard title="订单量趋势" subtitle="近30天每日订单数">
        <template #extra>
          <button class="ico-btn" title="展开详情" @click="openTimelineDetail">
            <AppIcon name="maximize" :size="14" color="var(--text2)" />
          </button>
        </template>
        <EChartBox :option="trendOpt" :height="240" />
      </AppCard>
    </div>
    <AppCard title="订单明细" subtitle="所有订单列表（每页20条）">
      <template #extra>
        <div class="filters">
          <button v-for="s in statusOpts" :key="s" class="fbtn" :class="{ active: filter === s }" @click="onFilter(s)">{{ s }}</button>
        </div>
      </template>
      <DataTable :columns="cols" :data="(orders as Record<string,unknown>[])" :pagination="true" :page-size="20" />
    </AppCard>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, h, onMounted } from 'vue'
import type { EChartsOption } from 'echarts'
import PageHeader from '@/components/common/PageHeader.vue'
import KpiCard    from '@/components/common/KpiCard.vue'
import AppCard    from '@/components/common/AppCard.vue'
import EChartBox  from '@/components/common/EChartBox.vue'
import DataTable  from '@/components/common/DataTable.vue'
import LegendItem from '@/components/common/LegendItem.vue'
import { TOOLTIP_BASE, ORDER_STATUS_ZH, ORDER_STATUS_EN, fmtDateTime, recentDayLabels, AXIS_GRID, xName, yName, fmtMoneyCN } from '@/utils/constants'
import type { TableColumn, OrderListItem } from '@/types'
import { api } from '@/services/api'
import { useDebouncedReload } from '@/composables/useEventStream'
import { useChartDetail } from '@/composables/useChartDetail'
import AppIcon from '@/components/common/AppIcon.vue'

const COLOR_MAP: Record<string,string> = { '待支付':'#f59e0b','已支付':'#3b82f6','已发货':'#8b5cf6','已完成':'#52b788','已取消':'#9ca3af','已退款':'#ef4444' }
const BADGE_BG: Record<string,string>  = { '待支付':'#fef9c3','已支付':'#dbeafe','已发货':'#ede9fe','已完成':'#dcfce7','已取消':'#f3f4f6','已退款':'#fee2e2' }
const BADGE_FG: Record<string,string>  = { '待支付':'#ca8a04','已支付':'#1d4ed8','已发货':'#7c3aed','已完成':'#15803d','已取消':'#6b7280','已退款':'#dc2626' }

const statusOpts = ['全部','待支付','已支付','已发货','已完成','已取消','已退款']
const filter = ref('全部')

const overview   = ref<Record<string, number>>({})
const statusDist = ref<{ name: string; count: number; pct: number }[]>([])
const timeline   = ref<{ date: string; order_count: number }[]>([])
const orders     = ref<Array<{ id: string; username: string; amount: number; status: string; time: string }>>([])

async function loadOrders() {
  const status = filter.value === '全部' ? undefined : ORDER_STATUS_EN[filter.value]
  const resp = await api.getOrdersList(1, 100, status)
  const list: OrderListItem[] = resp?.data ?? []
  orders.value = list.map(o => ({
    id: o.order_no,
    username: o.customer,
    amount: o.total_amount,
    status: ORDER_STATUS_ZH[o.status] ?? o.status,
    time: fmtDateTime(o.created_at),
  }))
}

function onFilter(s: string) {
  filter.value = s
  loadOrders()
}

async function loadData() {
  try {
    const [ovw, byStatus, tl] = await Promise.all([
      api.getOrdersOverview('30'),
      api.getOrdersByStatus('30'),
      api.getOrderTimeline(30),
    ])
    overview.value = ovw ?? {}

    const byStatusList: { status: string; count: number; percentage: number }[] = byStatus?.data ?? []
    statusDist.value = byStatusList.map(s => ({
      name: ORDER_STATUS_ZH[s.status] ?? s.status,
      count: s.count,
      pct: Math.round(s.percentage),
    }))

    timeline.value = tl?.data ?? []
    await loadOrders()
  } catch (e) {
    console.error('[OrderView] load failed', e)
  }
}

onMounted(loadData)
// order:订单 KPI / 状态分布 / 时间线;refund:退款分析详情;customer:订单列表显示客户名变化
useDebouncedReload(['order', 'refund', 'customer'], loadData)

const { open } = useChartDetail()

function openStatusDetail() {
  open({
    title: '订单状态分布 · 近 90 天',
    subtitle: '按状态聚合 + 各状态最近订单',
    load: async () => {
      const byStatus = await api.getOrdersByStatus('90')
      const list: { status: string; count: number; amount: number; percentage: number }[] = byStatus?.data ?? []
      const chartOption: EChartsOption = {
        tooltip:{trigger:'item', ...TOOLTIP_BASE, formatter:(p:any)=>`${p.name}: ${p.value} (${p.percent}%)`},
        legend:{top:0},
        series:[{type:'pie', radius:['40%','70%'], data: list.map(s=>({
          name: ORDER_STATUS_ZH[s.status] ?? s.status,
          value: s.count,
          itemStyle:{ color: COLOR_MAP[ORDER_STATUS_ZH[s.status] ?? s.status] ?? '#999' },
        })), label:{show:true, formatter:'{b}\n{d}%'}}],
      }
      const cols: TableColumn[] = [
        { key:'name', title:'状态' },
        { key:'count', title:'订单数', align:'right', render:v=>(v as number).toLocaleString() },
        { key:'amount', title:'金额', align:'right', render:v=>`¥${(v as number).toLocaleString(undefined,{maximumFractionDigits:0})}` },
        { key:'percentage', title:'占比', align:'right', render:v=>`${(v as number).toFixed(1)}%` },
      ]
      const rows = list.map(s => ({
        name: ORDER_STATUS_ZH[s.status] ?? s.status,
        count: s.count,
        amount: s.amount,
        percentage: s.percentage,
      }))
      return { chartOption, columns: cols, rows: rows as unknown as Record<string,unknown>[] }
    },
  })
}

function openTimelineDetail() {
  open({
    title: '订单量趋势 · 近 30 天',
    load: async () => {
      const r = await api.getOrderTimeline(30)
      const tl = (r?.data ?? []) as { date: string; order_count: number; total_amount: number; avg_order_value: number }[]
      const labels = tl.map(t => t.date.slice(5))
      const chartOption: EChartsOption = {
        tooltip:{trigger:'axis', ...TOOLTIP_BASE},
        legend:{top:0, data:['订单数','销售额']},
        grid:{ ...AXIS_GRID, top: 60 },
        xAxis:{type:'category', ...xName('日期'), data: labels, axisLabel:{interval:Math.max(1,Math.floor(labels.length/12))}},
        yAxis:[
          { type:'value', ...yName('订单数 (单)'), splitLine:{lineStyle:{color:'#f0f4f1'}}, axisLabel:{formatter:(v:number)=>`${v} 单`} },
          { type:'value', ...yName('销售额 (¥)'), splitLine:{show:false}, axisLabel:{formatter:(v:number)=>fmtMoneyCN(v, { wanDecimals: 0 })} },
        ],
        series:[
          { name:'订单数', type:'bar', data: tl.map(t=>t.order_count), itemStyle:{color:'rgba(82,183,136,.7)', borderRadius:[3,3,0,0]}, barMaxWidth:10 },
          { name:'销售额', type:'line', yAxisIndex:1, data: tl.map(t=>t.total_amount), smooth:true, lineStyle:{color:'#6366f1',width:2.5}, symbol:'none' },
        ],
      }
      const cols: TableColumn[] = [
        { key:'date', title:'日期' },
        { key:'order_count', title:'订单数', align:'right' },
        { key:'total_amount', title:'销售额', align:'right', render:v=>`¥${(v as number).toLocaleString(undefined,{maximumFractionDigits:0})}` },
        { key:'avg_order_value', title:'客单价', align:'right', render:v=>`¥${(v as number).toFixed(2)}` },
      ]
      // 图表保持 ASC(左→右=过去→今天),表格按日期 DESC(今天在最上)
      const tableRows = [...tl].reverse()
      return { chartOption, columns: cols, rows: tableRows as unknown as Record<string,unknown>[] }
    },
  })
}

const statusOpt = computed<EChartsOption>(() => ({
  tooltip: { trigger:'item', ...TOOLTIP_BASE },
  series: [{
    type:'pie',
    radius:['50%','72%'],
    avoidLabelOverlap: true,
    data: statusDist.value.map(s=>({ name:s.name, value:s.count, itemStyle:{color:COLOR_MAP[s.name]} })),
    label: { show: true, formatter: '{b}\n{d}%', fontSize: 11, fontWeight: 700, color: 'inherit' },
    labelLine: { show: true, length: 6, length2: 6, lineStyle: { color: 'inherit' } },
    emphasis: { scale: true, scaleSize: 6, label: { fontSize: 13 } },
  }],
}))

const trendOpt = computed<EChartsOption>(() => {
  const days = timeline.value.length || 30
  const labels = timeline.value.length
    ? timeline.value.map(t => {
        const [, m, d] = t.date.split('-')
        return `${parseInt(m)}/${parseInt(d)}`
      })
    : recentDayLabels(30)
  const data = timeline.value.map(t => t.order_count)
  return {
    tooltip: { trigger:'axis', ...TOOLTIP_BASE, formatter:(p:unknown)=>{const params=p as {value:number}[];return `${params[0].value} 单`} },
    grid: AXIS_GRID,
    xAxis: { type:'category', ...xName('日期'), data:labels, axisLine:{show:false}, axisTick:{show:false}, splitLine:{show:false}, axisLabel:{interval: Math.max(1, Math.floor(days/6))} },
    yAxis: { type:'value', ...yName('订单数 (单)'), splitLine:{lineStyle:{color:'#f0f4f1'}}, axisLabel:{formatter:(v:number)=>`${v} 单`} },
    series: [{ type:'line', data, smooth:true, lineStyle:{color:'#52b788',width:2.5}, areaStyle:{color:'rgba(82,183,136,.08)'}, symbol:'none' }],
  }
})

const cols: TableColumn[] = [
  { key:'id',       title:'订单号', render:v=>h('span',{style:{fontFamily:'monospace',fontSize:'12px',color:'var(--text2)'}},v) },
  { key:'username', title:'用户名' },
  { key:'amount',   title:'订单金额', align:'right', render:v=>h('span',{style:{fontWeight:700}},`¥${(v as number).toFixed(2)}`) },
  { key:'status',   title:'状态', render:v=>h('span',{style:{display:'inline-flex',alignItems:'center',padding:'2px 9px',borderRadius:'99px',fontSize:'12px',fontWeight:700,background:BADGE_BG[v as string]||'#f1f5f0',color:BADGE_FG[v as string]||'#4b5563'}},v) },
  { key:'time',     title:'下单时间', render:v=>h('span',{style:{fontSize:'12px',color:'var(--text2)'}},v) },
]
</script>

<style scoped>
.kpi-grid       { display:grid; grid-template-columns:repeat(4, 1fr); gap:16px; }
@media (max-width: 1100px) { .kpi-grid { grid-template-columns:repeat(2, 1fr); } }
.grid-side-main { display:grid; grid-template-columns:320px 1fr; gap:16px; }
.filters     { display:flex; gap:6px; flex-wrap:wrap; }
.fbtn        { padding:5px 12px; border-radius:7px; font-size:12px; font-weight:700; border:none; background:var(--green-50); color:var(--green-dark); cursor:pointer; transition:all .15s; }
.fbtn.active { background:var(--green); color:#fff; }
</style>
