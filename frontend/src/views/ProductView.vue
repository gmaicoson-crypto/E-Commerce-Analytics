<template>
  <div class="fade-in">
    <PageHeader title="商品分析" subtitle="商品销量、库存及趋势分析" />

    <div class="kpi-row mb16">
      <KpiCard title="总商品数"   :value="overviewKpi.total_products.toLocaleString()"        icon="products"     icon-bg="#dcfce7" />
      <KpiCard title="在售商品"   :value="overviewKpi.on_sale.toLocaleString()"                icon="checkCircle"  icon-bg="#dbeafe" />
      <KpiCard title="低库存预警" :value="overviewKpi.low_stock_count.toLocaleString()"        icon="alertCircle"  icon-bg="#fee2e2" />
      <KpiCard title="总库存价值" :value="fmtMoneyCN(overviewKpi.total_inventory_value, { prefix: '' })" prefix="¥" icon="finance" icon-bg="#ede9fe" />
    </div>

    <div class="grid-equal-2 mb16">
      <AppCard title="品类销量占比" class="equal-card">
        <template #extra>
          <button class="ico-btn" title="展开详情" @click="openCategoryDetail">
            <AppIcon name="maximize" :size="14" color="var(--text2)" />
          </button>
        </template>
        <EChartBox :option="catOpt" :height="240" />
        <div class="legend-list">
          <LegendItem v-for="(c,i) in catData" :key="c.name" :color="PAL[i]" :label="c.name" :pct="c.pct" />
        </div>
      </AppCard>
      <AppCard title="TOP5商品销量趋势" subtitle="近30天各商品日销量(含今日)" class="equal-card">
        <template #extra>
          <button class="ico-btn" title="展开详情" @click="openTop5TrendDetail">
            <AppIcon name="maximize" :size="14" color="var(--text2)" />
          </button>
        </template>
        <EChartBox :option="trendOpt" :height="320" />
      </AppCard>
    </div>

    <div class="grid-equal-2 mb16">
      <AppCard title="商品销量 TOP10" subtitle="近30天销售额排行" class="equal-card">
        <div class="scroll-body">
          <DataTable :columns="top10Cols" :data="(top10 as Record<string,unknown>[])" />
        </div>
      </AppCard>
      <AppCard title="库存预警明细" subtitle="库存低于预警阈值的商品" class="equal-card">
        <template #extra><AppBadge :label="`${inventory.length}条`" color="red" /></template>
        <div class="scroll-body">
          <DataTable :columns="invCols" :data="(inventory as Record<string,unknown>[])" />
        </div>
      </AppCard>
    </div>

    <AppCard title="商品列表 · 销售表现 TOP20">
      <template #extra>
        <button class="ico-btn" title="展开详情" @click="openProductList20Detail">
          <AppIcon name="maximize" :size="14" color="var(--text2)" />
        </button>
      </template>
      <DataTable :columns="listCols" :data="(productList as Record<string,unknown>[])" />
    </AppCard>
  </div>
</template>

<script setup lang="ts">
import { h, ref, computed, onMounted } from 'vue'
import type { EChartsOption } from 'echarts'
import PageHeader from '@/components/common/PageHeader.vue'
import AppCard    from '@/components/common/AppCard.vue'
import AppBadge   from '@/components/common/AppBadge.vue'
import EChartBox  from '@/components/common/EChartBox.vue'
import DataTable  from '@/components/common/DataTable.vue'
import LegendItem from '@/components/common/LegendItem.vue'
import KpiCard    from '@/components/common/KpiCard.vue'
import { CHART_PALETTE as PAL, TOOLTIP_BASE, AXIS_GRID, xName, yName, fmtMoneyCN } from '@/utils/constants'
import type { TableColumn, ProductPerformance, LowStockProduct } from '@/types'
import { api } from '@/services/api'
import { useDebouncedReload } from '@/composables/useEventStream'
import { useChartDetail } from '@/composables/useChartDetail'
import AppIcon from '@/components/common/AppIcon.vue'

const performance  = ref<ProductPerformance[]>([])
const lowStock     = ref<LowStockProduct[]>([])
const categoryRaw  = ref<{ category: string; count: number }[]>([])
const overviewKpi  = ref({
  total_products: 0,
  on_sale: 0,
  off_sale: 0,
  low_stock_count: 0,
  total_stock: 0,
  total_inventory_value: 0,
})

interface TopTrendProduct { product_id: number; product_name: string; category: string | null; total_qty: number; daily: number[] }
interface TopTrendResp { period_days: number; dates: string[]; products: TopTrendProduct[] }
const topTrend = ref<TopTrendResp>({ period_days: 30, dates: [], products: [] })

const top10 = computed(() =>
  performance.value.slice(0, 10).map((p, i) => ({
    rank: i + 1,
    name: p.product_name,
    category: p.category,
    qty: p.quantity_sold,
    amount: p.sales,
  })),
)

const inventory = computed(() =>
  lowStock.value.map((p) => ({
    name: p.product_name,
    category: p.category,
    stock: p.stock,
    threshold: p.low_stock_threshold,
    status: p.stock < p.low_stock_threshold / 2 ? '严重' : '预警',
  })),
)

const productList = computed(() =>
  performance.value.slice(0, 20).map((p) => ({
    name: p.product_name,
    category: p.category,
    qty: p.quantity_sold,
    price: p.price,
    sales: p.sales,
    profit_margin: p.profit_margin,
  })),
)

const catData = computed(() => {
  const total = categoryRaw.value.reduce((a, c) => a + c.count, 0) || 1
  return categoryRaw.value
    .map((c) => ({ name: c.category, pct: Math.round((c.count / total) * 100) }))
    .sort((a, b) => b.pct - a.pct)
})

async function loadData() {
  try {
    const [perf, low, byCat, ovw, trend] = await Promise.all([
      api.getProductsPerformance('30'),
      api.getLowStockProducts(),
      api.getProductsByCategory(),
      api.getProductsOverview(),
      api.getTopProductsTrend(30, 5),
    ])
    performance.value = perf?.data ?? []
    lowStock.value   = low?.data ?? []
    categoryRaw.value = (byCat ?? []) as { category: string; count: number }[]
    if (ovw) overviewKpi.value = ovw
    topTrend.value = (trend as TopTrendResp) ?? { period_days: 30, dates: [], products: [] }
  } catch (e) {
    console.error('[ProductView] load failed', e)
  }
}

onMounted(loadData)
useDebouncedReload(['product', 'order'], loadData)

const { open } = useChartDetail()

function openCategoryDetail() {
  open({
    title: '品类商品分布',
    subtitle: '各品类商品数量 / 在售 / 库存 / 均价',
    load: async () => {
      const data = (await api.getProductsByCategory()) as { category: string; count: number; on_sale: number; avg_price: number; avg_cost: number; total_stock: number }[]
      const totalCount = data.reduce((a,c)=>a+c.count,0) || 1
      const chartOption: EChartsOption = {
        tooltip:{trigger:'item', ...TOOLTIP_BASE, formatter:(p:any)=>`${p.name}: ${p.value} 件 (${p.percent}%)`},
        legend:{top:0},
        series:[{type:'pie', radius:['40%','70%'], data: data.map((c,i)=>({name:c.category, value:c.count, itemStyle:{color:PAL[i % PAL.length]}})), label:{show:true, formatter:'{b}\n{d}%'}}],
      }
      const cols: TableColumn[] = [
        { key:'category', title:'品类' },
        { key:'count', title:'商品数', align:'right' },
        { key:'on_sale', title:'在售', align:'right' },
        { key:'total_stock', title:'总库存', align:'right', render:v=>(v as number).toLocaleString() },
        { key:'avg_price', title:'均价', align:'right', render:v=>`¥${(v as number).toFixed(2)}` },
        { key:'avg_cost', title:'均成本', align:'right', render:v=>`¥${(v as number).toFixed(2)}` },
        { key:'pct', title:'占比', align:'right', render:(_,row)=>`${(((row as any).count/totalCount)*100).toFixed(1)}%` },
      ]
      return { chartOption, columns: cols, rows: data as unknown as Record<string,unknown>[] }
    },
  })
}

/** TOP5 商品销量趋势 — 真实日级聚合 */
function openTop5TrendDetail() {
  open({
    title: 'TOP5 商品销量趋势 · 近 30 天',
    subtitle: '按已支付订单聚合的日级真实销量(含今日)',
    load: async () => {
      const [trendResp, perfResp] = await Promise.all([
        api.getTopProductsTrend(30, 5),
        api.getProductsPerformance('30', 5),
      ])
      const trend = (trendResp as TopTrendResp) ?? { period_days: 30, dates: [], products: [] }
      const perf = (perfResp?.data ?? []) as ProductPerformance[]
      const labels = trend.dates.map(d => d.slice(5))
      const chartOption: EChartsOption = {
        tooltip: { trigger:'axis', ...TOOLTIP_BASE },
        legend: {
          top: 0,
          data: trend.products.map(p => p.product_name.slice(0, 16)),
          itemWidth: 10, itemHeight: 10, icon: 'circle',
        },
        grid: { ...AXIS_GRID, top: 60 },
        xAxis: { type:'category', ...xName('日期'), data: labels, axisLabel:{ interval: Math.max(1, Math.floor(labels.length/12)) } },
        yAxis: { type:'value', ...yName('日销量 (件)'), minInterval:1, splitLine:{ lineStyle:{ color:'#f0f4f1' } }, axisLabel:{ formatter:(v:number)=>`${v}件` } },
        series: trend.products.map((p, i) => ({
          type: 'line',
          name: p.product_name.slice(0, 16),
          smooth: true,
          data: p.daily,
          lineStyle: { color: VIVID5[i % VIVID5.length], width: 2.5 },
          areaStyle: { color: `${VIVID5[i % VIVID5.length]}15` },
          symbol: 'none',
        })),
      }
      const cols: TableColumn[] = [
        { key:'rank',          title:'排名', align:'right' },
        { key:'product_name',  title:'商品名', wrap:true },
        { key:'category',      title:'品类' },
        { key:'price',         title:'售价',   align:'right', render:v=>`¥${(v as number).toFixed(2)}` },
        { key:'quantity_sold', title:'销量',   align:'right', render:v=>(v as number).toLocaleString() },
        { key:'sales',         title:'销售额', align:'right', render:v=>`¥${(v as number).toLocaleString(undefined,{maximumFractionDigits:0})}` },
        { key:'profit_margin', title:'毛利率', align:'right', render:v=>`${(v as number).toFixed(1)}%` },
      ]
      const tableRows = perf.map((r, i) => ({ rank: i + 1, ...r }))
      return { chartOption, columns: cols, rows: tableRows as unknown as Record<string,unknown>[] }
    },
  })
}

/** 商品列表 · 销售表现 TOP20 — TOP20 销售额排行 + 全部 20 条明细 */
function openProductList20Detail() {
  open({
    title: '商品列表 · 销售表现 TOP20 · 近 90 天',
    load: async () => {
      const r = await api.getProductsPerformance('90', 20)
      const rows = (r?.data ?? []) as ProductPerformance[]
      const chartOption: EChartsOption = {
        tooltip:{ trigger:'axis', axisPointer:{ type:'shadow' }, ...TOOLTIP_BASE,
          formatter:(p:any)=>`${p[0].name}: ${fmtMoneyCN(p[0].value)}` },
        grid: AXIS_GRID,
        xAxis:{ type:'value', ...xName('销售额 (¥)'), splitLine:{ lineStyle:{ color:'#f0f4f1' } }, axisLabel:{ formatter:(v:number)=>fmtMoneyCN(v, { wanDecimals: 0 }) } },
        yAxis:{ type:'category', ...yName('商品'), data: rows.map(p=>p.product_name.slice(0,16)).reverse(), axisLine:{ show:false }, axisTick:{ show:false } },
        series:[{
          type:'bar',
          data: rows.map(p=>p.sales).reverse(),
          itemStyle:{ color:'rgba(82,183,136,.85)', borderRadius:[0,4,4,0] },
          barMaxWidth: 16,
          label:{ show:true, position:'right', formatter:(p:any)=>fmtMoneyCN(p.value), fontSize:11, color:'var(--text2)' },
        }],
      }
      const cols: TableColumn[] = [
        { key:'rank',          title:'排名', align:'right' },
        { key:'product_name',  title:'商品名', wrap:true },
        { key:'category',      title:'品类' },
        { key:'price',         title:'售价',   align:'right', render:v=>`¥${(v as number).toFixed(2)}` },
        { key:'quantity_sold', title:'销量',   align:'right', render:v=>(v as number).toLocaleString() },
        { key:'sales',         title:'销售额', align:'right', render:v=>`¥${(v as number).toLocaleString(undefined,{maximumFractionDigits:0})}` },
        { key:'profit',        title:'毛利',   align:'right', render:v=>`¥${(v as number).toLocaleString(undefined,{maximumFractionDigits:0})}` },
        { key:'profit_margin', title:'毛利率', align:'right', render:v=>`${(v as number).toFixed(1)}%` },
      ]
      const tableRows = rows.map((r, i) => ({ rank: i + 1, ...r }))
      return { chartOption, columns: cols, rows: tableRows as unknown as Record<string,unknown>[] }
    },
  })
}

const badge = (v: string, ok: string, ng: string) =>
  h('span', { style: { display:'inline-flex',alignItems:'center',padding:'2px 9px',borderRadius:'99px',fontSize:'12px',fontWeight:700, background: v===ok?'#dcfce7':v===ng?'#fee2e2':'#fef9c3', color: v===ok?'#15803d':v===ng?'#dc2626':'#ca8a04' } }, v)

const top10Cols: TableColumn[] = [
  { key:'rank',     title:'排名', render: (v) => h('span',{style:{display:'inline-flex',alignItems:'center',justifyContent:'center',width:'24px',height:'24px',borderRadius:'6px',fontSize:'12px',fontWeight:800, background:(v as number)<=3?['#fef9c3','#f1f5f0','#ffedd5'][(v as number)-1]:'var(--bg)', color:(v as number)<=3?['#ca8a04','#6b7280','#ea580c'][(v as number)-1]:'var(--text3)'}},v) },
  { key:'name',     title:'商品名称', wrap:true },
  { key:'category', title:'品类' },
  { key:'qty',      title:'销量',   align:'right', render: v => `${(v as number).toLocaleString()} 件` },
  { key:'amount',   title:'销售额', align:'right', render: v => fmtMoneyCN(v as number) },
]
const invCols: TableColumn[] = [
  { key:'name',      title:'商品名称', wrap:true },
  { key:'category',  title:'品类' },
  { key:'stock',     title:'当前库存', align:'right', render: v => h('span',{style:{fontWeight:800,color:(v as number)<20?'#dc2626':'#f59e0b'}},v) },
  { key:'threshold', title:'预警阈值', align:'right' },
  { key:'status',    title:'状态', render: v => badge(v as string,'','严重') },
]
const listCols: TableColumn[] = [
  { key:'name',     title:'商品名称', wrap:true },
  { key:'category', title:'品类' },
  { key:'qty',      title:'销售数量', align:'right', render: v => (v as number).toLocaleString() },
  { key:'price',    title:'售价', align:'right', render: v => `¥${(v as number).toFixed(2)}` },
  { key:'sales',    title:'销售额', align:'right', render: v => fmtMoneyCN(v as number) },
  { key:'profit_margin', title:'毛利率', align:'right', render: v => `${(v as number).toFixed(1)}%` },
]

const VIVID5 = ['#6366f1','#f59e0b','#ec4899','#06b6d4','#f97316']
const trendOpt = computed<EChartsOption>(() => {
  const products = topTrend.value.products
  const labels = topTrend.value.dates.map(d => d.slice(5))  // MM-DD
  return {
    tooltip: { trigger:'axis', ...TOOLTIP_BASE },
    legend: { top:0, data: products.map(p=>p.product_name.slice(0,12)), itemWidth:8, itemHeight:8, icon:'circle', textStyle:{fontSize:11} },
    grid: { ...AXIS_GRID, top: 60 },
    xAxis: { type:'category', ...xName('日期'), data:labels, axisLine:{show:false}, axisTick:{show:false}, splitLine:{show:false}, axisLabel:{interval:Math.max(1, Math.floor(labels.length/8))} },
    yAxis: { type:'value', ...yName('日销量 (件)'), minInterval:1, splitLine:{lineStyle:{color:'#f0f4f1'}}, axisLabel:{formatter:(v:number)=>`${v}件`} },
    series: products.map((p, i) => ({
      type:'line',
      name: p.product_name.slice(0, 12),
      smooth:true,
      data: p.daily,
      lineStyle:{color:VIVID5[i % VIVID5.length],width:2},
      areaStyle:{color:`${VIVID5[i % VIVID5.length]}15`},
      symbol:'none',
    })),
  }
})
const catOpt = computed<EChartsOption>(() => ({
  tooltip: { trigger:'item', ...TOOLTIP_BASE, formatter:(p:any)=>`${p.name}: ${p.value}%` },
  series: [{
    type:'pie',
    radius:['45%','72%'],
    avoidLabelOverlap:true,
    data: catData.value.map((c,i)=>({ name:c.name, value:c.pct, itemStyle:{color:PAL[i]} })),
    label: { show:true, formatter:'{b}\n{c}%', fontSize:11, fontWeight:700, color:'inherit' },
    labelLine: { show:true, length:8, length2:8, lineStyle:{color:'inherit'} },
    emphasis: { scale:true, scaleSize:6, label:{ fontSize:13 } },
  }],
}))
</script>

<style scoped>
/* 视图局部:让 AppCard body 撑满 grid 行,使图表/表格在卡内填满 */
.equal-card                   { display:flex; flex-direction:column; height:100%; }
.equal-card :deep(.card)      { height:100%; display:flex; flex-direction:column; }
.equal-card :deep(.card-body) { flex:1; display:flex; flex-direction:column; min-height:0; }
.legend-list                  { margin-top:14px; display:grid; grid-template-columns:repeat(2, 1fr); gap:6px 18px; }
.scroll-body                  { flex:1; max-height:440px; overflow-y:auto; }
</style>
