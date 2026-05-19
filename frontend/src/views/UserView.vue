<template>
  <div class="fade-in">
    <PageHeader title="用户分析" subtitle="用户规模、结构及增长趋势" />
    <div class="kpi-row">
      <KpiCard title="总用户数"     :value="overview.total_customers?.toLocaleString() ?? '—'"     icon="users"   icon-bg="#dcfce7" />
      <KpiCard title="新客数"       :value="overview.new_customers?.toLocaleString() ?? '—'"       icon="plus"    icon-bg="#dbeafe" />
      <KpiCard title="复购客数"     :value="overview.returning_customers?.toLocaleString() ?? '—'" icon="refresh" icon-bg="#ede9fe" />
    </div>
    <div class="grid-3 mb16">
      <AppCard title="新老客比例">
        <template #extra>
          <button class="ico-btn" title="展开详情" @click="openCustomerTypeDetail">
            <AppIcon name="maximize" :size="14" color="var(--text2)" />
          </button>
        </template>
        <div class="pie-stack">
          <EChartBox :option="newOldOpt" :height="130" />
          <div class="legend-block">
            <LegendItem color="#74c69d" label="新客" :value="overview.new_customers?.toLocaleString() ?? '—'"       :pct="newPct" />
            <LegendItem color="#2d6a4f" label="老客" :value="overview.returning_customers?.toLocaleString() ?? '—'" :pct="100 - newPct" />
          </div>
        </div>
      </AppCard>
      <AppCard title="用户注册趋势" subtitle="近30天新增注册">
        <template #extra>
          <button class="ico-btn" title="展开详情" @click="openRegistrationDetail">
            <AppIcon name="maximize" :size="14" color="var(--text2)" />
          </button>
        </template>
        <EChartBox :option="regOpt" :height="300" />
      </AppCard>
      <AppCard title="性别分布">
        <template #extra>
          <button class="ico-btn" title="展开详情" @click="openGenderDetail">
            <AppIcon name="maximize" :size="14" color="var(--text2)" />
          </button>
        </template>
        <div class="pie-stack">
          <EChartBox :option="genderOpt" :height="130" />
          <div class="legend-block">
            <LegendItem v-for="g in genderData" :key="g.gender" :color="g.gender==='male'?'#52b788':'#b7e4c7'" :label="g.gender==='male'?'男性':'女性'" :value="g.count.toLocaleString()" :pct="Math.round(g.percentage)" />
          </div>
        </div>
      </AppCard>
    </div>
    <div class="grid-map-side mb16">
      <AppCard title="省份用户分布" subtitle="中国地图 · 颜色深浅代表用户数量">
        <template #extra>
          <button class="ico-btn" title="展开详情" @click="openProvinceDetail">
            <AppIcon name="maximize" :size="14" color="var(--text2)" />
          </button>
        </template>
        <EChartBox :option="provinceOpt" :height="540" />
      </AppCard>
      <div class="side-col">
        <AppCard title="省份用户 TOP10" subtitle="用户数量排行榜">
          <div class="province-scroll">
            <DataTable :columns="provinceCols" :data="(provinceTable as Record<string,unknown>[])" />
          </div>
        </AppCard>
        <AppCard title="用户年龄段分布">
          <template #extra>
            <button class="ico-btn" title="展开详情" @click="openAgeDetail">
              <AppIcon name="maximize" :size="14" color="var(--text2)" />
            </button>
          </template>
          <EChartBox :option="ageOpt" :height="220" />
        </AppCard>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { h, ref, computed, onMounted } from 'vue'
import type { EChartsOption } from 'echarts'
import PageHeader from '@/components/common/PageHeader.vue'
import KpiCard    from '@/components/common/KpiCard.vue'
import AppCard    from '@/components/common/AppCard.vue'
import EChartBox  from '@/components/common/EChartBox.vue'
import DataTable  from '@/components/common/DataTable.vue'
import LegendItem from '@/components/common/LegendItem.vue'
import { TOOLTIP_BASE, AXIS_GRID, xName, yName } from '@/utils/constants'
import type { TableColumn } from '@/types'
import { api } from '@/services/api'
import { useDebouncedReload } from '@/composables/useEventStream'
import { useChartDetail } from '@/composables/useChartDetail'
import AppIcon from '@/components/common/AppIcon.vue'
import { ensureChinaMap, toFullProvinceName } from '@/utils/chinaMap'

const mapReady = ref(false)

const overview = ref<Record<string, number>>({})
const genderData   = ref<{ gender: string; count: number; percentage: number }[]>([])
const ageData      = ref<{ age_group: string; count: number; percentage: number }[]>([])
const provinceData = ref<{ province: string; count: number }[]>([])
const growthData   = ref<{ date: string; new_users: number }[]>([])

const newPct = computed(() => {
  const tot = (overview.value.new_customers ?? 0) + (overview.value.returning_customers ?? 0)
  return tot > 0 ? Math.round(((overview.value.new_customers ?? 0) / tot) * 100) : 0
})

const provinceTable = computed(() => {
  const total = provinceData.value.reduce((a, p) => a + p.count, 0) || 1
  return provinceData.value.slice(0, 10).map(p => ({
    name: p.province,
    users: p.count,
    pct: Math.round((p.count / total) * 1000) / 10,
  }))
})

const maxPct = computed(() => provinceTable.value[0]?.pct ?? 1)

async function loadData() {
  try {
    const [ovw, gen, age, prov, gr] = await Promise.all([
      api.getUsersOverview(),
      api.getUsersByGender(),
      api.getUsersByAgeGroup(),
      api.getUsersByProvince(),
      api.getUserGrowth(30),
    ])
    overview.value = ovw ?? {}
    genderData.value   = gen ?? []
    ageData.value      = age ?? []
    provinceData.value = prov?.data ?? []
    growthData.value   = gr?.data ?? []
  } catch (e) {
    console.error('[UserView] load failed', e)
  }
}

onMounted(() => {
  loadData()
  ensureChinaMap().then(() => { mapReady.value = true }).catch(() => {})
})
// customer:注册/编辑触发性别/年龄/省份分布刷新;order:下单触发 RFM + 活跃用户数刷新
useDebouncedReload(['customer', 'order'], loadData)

const { open } = useChartDetail()

const CUSTOMER_COLS: TableColumn[] = [
  { key:'id', title:'ID', align:'right' },
  { key:'username', title:'用户名' },
  { key:'gender', title:'性别', render:v=>v==='male'?'男':v==='female'?'女':'—' },
  { key:'age_group', title:'年龄段' },
  { key:'province', title:'省份' },
  { key:'customer_type', title:'类型', render:v=>v==='new'?'新客':v==='returning'?'老客':'—' },
  { key:'registered_at', title:'注册时间', render:v=>String(v ?? '').replace('T',' ').slice(0,16) },
]

function openCustomerTypeDetail() {
  open({
    title: '新老客比例 · 客户明细',
    subtitle: '默认展示新客,可按需切换 API',
    load: async () => {
      const r = await api.getCustomersList(1, 100, { customer_type: 'new' })
      const list = r?.data ?? []
      const chartOption: EChartsOption = {
        tooltip:{trigger:'item', ...TOOLTIP_BASE, formatter:(p:any)=>`${p.name}: ${p.value} (${p.percent}%)`},
        legend:{top:0},
        series:[{type:'pie', radius:['40%','70%'], data:[
          { name:'新客', value: overview.value.new_customers ?? 0, itemStyle:{color:'#74c69d'} },
          { name:'老客', value: overview.value.returning_customers ?? 0, itemStyle:{color:'#2d6a4f'} },
        ], label:{show:true, formatter:'{b}\n{d}%'}}],
      }
      return { chartOption, columns: CUSTOMER_COLS, rows: list }
    },
  })
}

function openRegistrationDetail() {
  open({
    title: '用户注册趋势 · 近 30 天',
    load: async () => {
      const r = await api.getUserGrowth(30)
      const rows = (r?.data ?? []) as { date: string; new_users: number; cumulative: number }[]
      const labels = rows.map(r=>r.date.slice(5))
      const chartOption: EChartsOption = {
        tooltip:{trigger:'axis', ...TOOLTIP_BASE},
        legend:{top:0, data:['每日新增','累计']},
        grid:{ ...AXIS_GRID, top: 60 },
        xAxis:{type:'category', ...xName('日期'), data: labels, axisLabel:{interval:Math.max(1,Math.floor(labels.length/12))}},
        yAxis:[
          { type:'value', ...yName('每日新增 (人)'), splitLine:{lineStyle:{color:'#f0f4f1'}} },
          { type:'value', ...yName('累计 (人)'), splitLine:{show:false} },
        ],
        series:[
          { name:'每日新增', type:'bar', data: rows.map(r=>r.new_users), itemStyle:{color:'rgba(82,183,136,.75)', borderRadius:[3,3,0,0]}, barMaxWidth:10 },
          { name:'累计', type:'line', yAxisIndex:1, data: rows.map(r=>r.cumulative), smooth:true, lineStyle:{color:'#6366f1',width:2.5}, symbol:'none' },
        ],
      }
      const cols: TableColumn[] = [
        { key:'date', title:'日期' },
        { key:'new_users', title:'新增', align:'right' },
        { key:'cumulative', title:'累计', align:'right', render:v=>(v as number).toLocaleString() },
      ]
      // 图表保持 ASC(左→右=过去→今天),表格按日期 DESC(今天在最上)
      const tableRows = [...rows].reverse()
      return { chartOption, columns: cols, rows: tableRows as unknown as Record<string,unknown>[] }
    },
  })
}

function openGenderDetail() {
  open({
    title: '按性别 · 客户明细',
    subtitle: '默认展示男性客户',
    load: async () => {
      const r = await api.getCustomersList(1, 100, { gender: 'male' })
      const list = r?.data ?? []
      const chartOption: EChartsOption = {
        tooltip:{trigger:'item', ...TOOLTIP_BASE, formatter:(p:any)=>`${p.name}: ${p.value} (${p.percent}%)`},
        legend:{top:0},
        series:[{type:'pie', radius:['40%','70%'], data: genderData.value.map(g=>({
          name: g.gender === 'male' ? '男性' : '女性',
          value: g.count,
          itemStyle:{ color: g.gender === 'male' ? '#52b788' : '#b7e4c7' },
        })), label:{show:true, formatter:'{b}\n{d}%'}}],
      }
      return { chartOption, columns: CUSTOMER_COLS, rows: list }
    },
  })
}

function openProvinceDetail() {
  open({
    title: '省份用户分布 · 中国地图',
    subtitle: '颜色深浅代表用户数量',
    load: async () => {
      await ensureChinaMap()
      const r = await api.getUsersByProvince()
      const data = (r?.data ?? []) as { province: string; count: number }[]
      const total = data.reduce((a,c)=>a+c.count,0) || 1
      const max = Math.max(1, ...data.map(p=>p.count))
      const chartOption: EChartsOption = {
        tooltip: { trigger:'item', ...TOOLTIP_BASE, formatter:(p:any)=>p.data?`${p.name}: ${p.data.value} 人`:`${p.name}: 0 人` },
        visualMap: {
          right:24, bottom:24, min:0, max, text:['多','少'],
          inRange:{color:['#f0fdf4','#74c69d','#2d6a4f']}, calculable:true,
        },
        series: [{
          type:'map', map:'china', roam:true,
          zoom: 1,
          layoutCenter: ['50%', '50%'],
          layoutSize: '95%',
          label:{ show:true, fontSize:11 },
          emphasis:{ label:{show:true, fontSize:13, fontWeight:700}, itemStyle:{areaColor:'#52b788'} },
          itemStyle:{ borderColor:'#fff', borderWidth:0.5 },
          data: data.map(p=>({ name: toFullProvinceName(p.province), value: p.count })),
        }],
      }
      const cols: TableColumn[] = [
        { key:'province', title:'省份' },
        { key:'count', title:'用户数', align:'right', render:v=>(v as number).toLocaleString() },
        { key:'pct', title:'占比', align:'right', render:(_,row)=>`${(((row as any).count/total)*100).toFixed(1)}%` },
      ]
      return { chartOption, columns: cols, rows: data as unknown as Record<string,unknown>[] }
    },
  })
}

function openAgeDetail() {
  open({
    title: '按年龄段 · 客户明细',
    subtitle: '默认展示 25-34 岁段',
    load: async () => {
      const r = await api.getCustomersList(1, 100, { age_group: '25-34' })
      const list = r?.data ?? []
      const chartOption: EChartsOption = {
        tooltip:{trigger:'axis', ...TOOLTIP_BASE},
        grid: AXIS_GRID,
        xAxis:{type:'category', ...xName('年龄段'), data: ageData.value.map(a=>a.age_group)},
        yAxis:{type:'value', ...yName('用户数 (人)'), splitLine:{lineStyle:{color:'#f0f4f1'}}, axisLabel:{formatter:(v:number)=>`${v}人`}},
        series:[{type:'bar', data: ageData.value.map((a,i)=>({
          value: a.count,
          itemStyle:{ color: `rgba(82,183,136,${1 - i * 0.15})` },
        })), barMaxWidth:60, itemStyle:{borderRadius:[4,4,0,0]}}],
      }
      return { chartOption, columns: CUSTOMER_COLS, rows: list }
    },
  })
}

const newOldOpt = computed<EChartsOption>(() => ({
  series: [{ type:'pie', radius:['55%','78%'], data:[
    { name:'新客', value: newPct.value, itemStyle:{color:'#74c69d'} },
    { name:'老客', value: 100 - newPct.value, itemStyle:{color:'#2d6a4f'} },
  ], label:{show:false} }],
}))

const genderOpt = computed<EChartsOption>(() => ({
  series: [{ type:'pie', radius:['55%','78%'], data: genderData.value.map(g => ({
    name: g.gender === 'male' ? '男性' : '女性',
    value: g.count,
    itemStyle: { color: g.gender === 'male' ? '#52b788' : '#b7e4c7' },
  })), label:{show:false} }],
}))

const regOpt = computed<EChartsOption>(() => {
  const labels = growthData.value.map(d => {
    const [, m, day] = d.date.split('-')
    return `${parseInt(m)}/${parseInt(day)}`
  })
  return {
    tooltip: { trigger:'axis', ...TOOLTIP_BASE },
    grid: AXIS_GRID,
    xAxis: { type:'category', ...xName('日期'), data: labels, axisLine:{show:false}, axisTick:{show:false}, splitLine:{show:false}, axisLabel:{interval: Math.max(1, Math.floor(labels.length/6))} },
    yAxis: { type:'value', ...yName('新增用户 (人)'), splitLine:{lineStyle:{color:'#f0f4f1'}}, axisLabel:{formatter:(v:number)=>`${v}人`} },
    series: [{ type:'line', data: growthData.value.map(d => d.new_users), smooth:true, lineStyle:{color:'#52b788',width:2.5}, areaStyle:{color:'rgba(82,183,136,.08)'}, symbol:'none' }],
  }
})

const ageOpt = computed<EChartsOption>(() => ({
  tooltip: { trigger:'axis', ...TOOLTIP_BASE },
  grid: AXIS_GRID,
  xAxis: { type:'category', ...xName('年龄段'), data: ageData.value.map(a => a.age_group), axisLine:{show:false}, axisTick:{show:false}, splitLine:{show:false} },
  yAxis: { type:'value', ...yName('用户数 (人)'), splitLine:{lineStyle:{color:'#f0f4f1'}}, axisLabel:{formatter:(v:number)=>`${v}人`} },
  series: [{ type:'bar', data: ageData.value.map((a, i) => ({
    value: a.count,
    itemStyle: { color: `rgba(82,183,136,${1 - i * 0.15})` },
  })), barMaxWidth:40, itemStyle:{borderRadius:[4,4,0,0]} }],
}))

const provinceOpt = computed<EChartsOption>(() => {
  if (!mapReady.value) {
    // 地图还没注册之前先显示一个占位空图
    return { series: [] }
  }
  const max = Math.max(1, ...provinceData.value.map(p => p.count))
  return {
    tooltip: {
      trigger: 'item',
      ...TOOLTIP_BASE,
      formatter: (p: any) => p.data ? `${p.name}: ${p.data.value} 人` : `${p.name}: 0 人`,
    },
    visualMap: {
      right: 12,
      bottom: 12,
      min: 0,
      max,
      text: ['多', '少'],
      inRange: { color: ['#f0fdf4', '#74c69d', '#2d6a4f'] },
      calculable: true,
      textStyle: { fontSize: 11, color: 'var(--text2)' },
    },
    series: [{
      type: 'map',
      map: 'china',
      roam: true,
      zoom: 1,
      layoutCenter: ['50%', '50%'],
      layoutSize: '92%',
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 12, fontWeight: 700 }, itemStyle: { areaColor: '#52b788' } },
      itemStyle: { borderColor: '#fff', borderWidth: 0.5 },
      data: provinceData.value.map(p => ({ name: toFullProvinceName(p.province), value: p.count })),
    }],
  }
})

const provinceCols: TableColumn[] = [
  { key:'name', title:'省份', render:(_, row, i) => h('span',{style:{display:'flex',alignItems:'center',gap:'8px'}},[
      h('span',{style:{width:'22px',height:'22px',borderRadius:'6px',fontSize:'12px',fontWeight:800,display:'inline-flex',alignItems:'center',justifyContent:'center',background:i<3?['#fef9c3','#f1f5f0','#ffedd5'][i]:'var(--bg)',color:i<3?['#ca8a04','#6b7280','#ea580c'][i]:'var(--text3)'}}, i+1),
      (row as {name:string}).name,
    ])
  },
  { key:'users', title:'用户数量', align:'right', render: v => (v as number).toLocaleString() },
  { key:'pct',   title:'占比', align:'right', render: v => h('div',{style:{display:'flex',alignItems:'center',gap:'8px',justifyContent:'flex-end'}},[
      h('div',{style:{width:'80px',height:'6px',borderRadius:'3px',background:'var(--border)',overflow:'hidden'}},[
        h('div',{style:{width:`${(v as number)/maxPct.value*100}%`,height:'100%',background:'var(--green)',borderRadius:'3px'}})
      ]),
      h('span',{style:{fontSize:'12px',fontWeight:700,minWidth:'40px',textAlign:'right'}}, `${v}%`),
    ])
  },
]
</script>

<style scoped>
.grid-3          { display:grid; grid-template-columns:220px 1fr 220px; gap:16px; }
.pie-stack       { display:flex; flex-direction:column; gap:10px; }
.legend-block    { display:flex; flex-direction:column; gap:4px; }
.grid-2          { display:grid; grid-template-columns:1fr 1fr; gap:16px; }
.grid-map-side   { display:grid; grid-template-columns:1.5fr 1fr; gap:16px; align-items:stretch; }
.side-col        { display:flex; flex-direction:column; gap:16px; min-height:0; }
.side-col > *    { flex:1 1 0; min-height:0; }
.province-scroll { max-height:240px; overflow-y:auto; }
</style>
