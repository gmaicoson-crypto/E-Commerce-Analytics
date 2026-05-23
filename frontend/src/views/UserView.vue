<template>
  <div class="fade-in">
    <PageHeader title="用户分析" subtitle="用户规模、结构及增长趋势" />

    <div class="kpi-row">
      <KpiCard
        title="总用户数"
        :value="overview.total_customers?.toLocaleString() ?? '—'"
        icon="users"
        icon-bg="#dcfce7"
      />
      <KpiCard
        title="新客数"
        :value="overview.new_customers?.toLocaleString() ?? '—'"
        icon="plus"
        icon-bg="#dbeafe"
      />
      <KpiCard
        title="复购客数"
        :value="overview.repeat_customers?.toLocaleString() ?? '—'"
        icon="refresh"
        icon-bg="#ede9fe"
      />
    </div>

    <div class="grid-3 mb16">
      <AppCard title="新老客比例">
        <template #extra>
          <button
            class="ico-btn"
            title="展开详情"
            @click="openCustomerTypeDetail"
          >
            <AppIcon name="maximize" :size="14" color="var(--text2)" />
          </button>
        </template>

        <div class="pie-stack">
          <EChartBox :option="newOldOpt" :height="130" />
          <div class="legend-block">
            <LegendItem
              color="#74c69d"
              label="新客"
              :value="overview.new_customers?.toLocaleString() ?? '—'"
              :pct="newPct"
            />
            <LegendItem
              color="#2d6a4f"
              label="老客"
              :value="overview.returning_customers?.toLocaleString() ?? '—'"
              :pct="100 - newPct"
            />
          </div>
        </div>
      </AppCard>

      <AppCard title="用户注册趋势" subtitle="近30天新增注册">
        <template #extra>
          <button
            class="ico-btn"
            title="展开详情"
            @click="openRegistrationDetail"
          >
            <AppIcon name="maximize" :size="14" color="var(--text2)" />
          </button>
        </template>

        <EChartBox :option="regOpt" :height="300" />
      </AppCard>

      <AppCard title="性别分布">
        <template #extra>
          <button
            class="ico-btn"
            title="展开详情"
            @click="openGenderDetail"
          >
            <AppIcon name="maximize" :size="14" color="var(--text2)" />
          </button>
        </template>

        <div class="pie-stack">
          <EChartBox :option="genderOpt" :height="130" />
          <div class="legend-block">
            <LegendItem
              v-for="gender in genderData"
              :key="gender.gender"
              :color="gender.gender === 'male' ? '#52b788' : '#b7e4c7'"
              :label="gender.gender === 'male' ? '男性' : '女性'"
              :value="gender.count.toLocaleString()"
              :pct="Math.round(gender.percentage)"
            />
          </div>
        </div>
      </AppCard>
    </div>

    <div class="grid-map-side mb16">
      <AppCard title="省份用户分布" subtitle="中国地图 · 颜色深浅代表用户数量">
        <template #extra>
          <button
            class="ico-btn"
            title="展开详情"
            @click="openProvinceDetail"
          >
            <AppIcon name="maximize" :size="14" color="var(--text2)" />
          </button>
        </template>

        <EChartBox :option="provinceOpt" :height="540" />
      </AppCard>

      <div class="side-col">
        <AppCard title="省份用户 TOP10" subtitle="用户数量排行榜">
          <div class="province-scroll">
            <DataTable
              :columns="provinceCols"
              :data="provinceTable as Record<string, unknown>[]"
            />
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
/* 用户分析页面。 */
import type { EChartsOption } from 'echarts'
import { computed, h, onMounted, ref } from 'vue'
import AppCard from '@/components/common/AppCard.vue'
import AppIcon from '@/components/common/AppIcon.vue'
import DataTable from '@/components/common/DataTable.vue'
import EChartBox from '@/components/common/EChartBox.vue'
import KpiCard from '@/components/common/KpiCard.vue'
import LegendItem from '@/components/common/LegendItem.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import { useChartDetail } from '@/composables/useChartDetail'
import { useDebouncedReload } from '@/composables/useEventStream'
import { api } from '@/services/api'
import type { TableColumn } from '@/types'
import { ensureChinaMap, toFullProvinceName } from '@/utils/chinaMap'
import { AXIS_GRID, TOOLTIP_BASE, xName, yName } from '@/utils/constants'

function toNumber(value: unknown): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : 0
}

function getTooltipValue(payload: unknown): number {
  const value = (payload as { value?: unknown })?.value
  return toNumber(value)
}

function getTooltipPercent(payload: unknown): number {
  const percent = (payload as { percent?: unknown })?.percent
  return toNumber(percent)
}

function getTooltipName(payload: unknown): string {
  const name = (payload as { name?: unknown })?.name
  return typeof name === 'string' ? name : ''
}

function getTooltipDataValue(payload: unknown): number {
  const value = (payload as { data?: { value?: unknown } })?.data?.value
  return toNumber(value)
}

const mapReady = ref(false)

const overview = ref<Record<string, number>>({})
const genderData = ref<{ gender: string; count: number; percentage: number }[]>(
  [],
)
const ageData = ref<{ age_group: string; count: number; percentage: number }[]>(
  [],
)
const provinceData = ref<{ province: string; count: number }[]>([])
const growthData = ref<{ date: string; new_users: number }[]>([])

const newPct = computed(() => {
  const total =
    (overview.value.new_customers ?? 0) +
    (overview.value.returning_customers ?? 0)

  return total > 0
    ? Math.round(((overview.value.new_customers ?? 0) / total) * 100)
    : 0
})

const provinceTable = computed(() => {
  const total = provinceData.value.reduce((sum, item) => sum + item.count, 0) || 1

  return provinceData.value.slice(0, 10).map((item) => ({
    name: item.province,
    users: item.count,
    pct: Math.round((item.count / total) * 1000) / 10,
  }))
})

const maxPct = computed(() => provinceTable.value[0]?.pct ?? 1)

async function loadData() {
  try {
    const [ovw, gender, age, province, growth] = await Promise.all([
      api.getUsersOverview(),
      api.getUsersByGender(),
      api.getUsersByAgeGroup(),
      api.getUsersByProvince(),
      api.getUserGrowth(30),
    ])

    overview.value = ovw ?? {}
    genderData.value = gender ?? []
    ageData.value = age ?? []
    provinceData.value = province?.data ?? []
    growthData.value = growth?.data ?? []
  } catch (e) {
    console.error('[UserView] load failed', e)
  }
}

onMounted(() => {
  loadData()
  ensureChinaMap()
    .then(() => {
      mapReady.value = true
    })
    .catch(() => {})
})

useDebouncedReload(['customer', 'order'], loadData)

const { open } = useChartDetail()

const CUSTOMER_COLS: TableColumn[] = [
  { key: 'id', title: 'ID', align: 'right' },
  { key: 'username', title: '用户名' },
  {
    key: 'gender',
    title: '性别',
    render: (value) =>
      value === 'male' ? '男' : value === 'female' ? '女' : '—',
  },
  { key: 'age_group', title: '年龄段' },
  { key: 'province', title: '省份' },
  {
    key: 'customer_type',
    title: '类型',
    render: (value) =>
      value === 'new' ? '新客' : value === 'returning' ? '老客' : '—',
  },
  {
    key: 'registered_at',
    title: '注册时间',
    render: (value) => String(value ?? '').replace('T', ' ').slice(0, 16),
  },
]

function openCustomerTypeDetail() {
  open({
    title: '新老客比例 · 客户明细',
    subtitle: '默认展示新客,可按需切换 API',
    load: async () => {
      const response = await api.getCustomersList(1, 10000, {
        customer_type: 'new',
      })
      const list = response?.data ?? []

      const chartOption: EChartsOption = {
        tooltip: {
          trigger: 'item',
          ...TOOLTIP_BASE,
          formatter: (payload: unknown) =>
            `${getTooltipName(payload)}: ${getTooltipValue(payload)} (${getTooltipPercent(payload)}%)`,
        },
        legend: { top: 0 },
        series: [
          {
            type: 'pie',
            radius: ['40%', '70%'],
            data: [
              {
                name: '新客',
                value: overview.value.new_customers ?? 0,
                itemStyle: { color: '#74c69d' },
              },
              {
                name: '老客',
                value: overview.value.returning_customers ?? 0,
                itemStyle: { color: '#2d6a4f' },
              },
            ],
            label: {
              show: true,
              formatter: '{b}\n{d}%',
            },
          },
        ],
      }

      return {
        chartOption,
        columns: CUSTOMER_COLS,
        rows: list,
      }
    },
  })
}

function openRegistrationDetail() {
  open({
    title: '用户注册趋势 · 近 30 天',
    load: async () => {
      const response = await api.getUserGrowth(30)
      const rows = (response?.data ?? []) as Array<{
        date: string
        new_users: number
        cumulative: number
      }>

      const labels = rows.map((row) => row.date.slice(5))
      const chartOption: EChartsOption = {
        tooltip: {
          trigger: 'axis',
          ...TOOLTIP_BASE,
        },
        legend: {
          top: 0,
          data: ['每日新增', '累计'],
        },
        grid: {
          ...AXIS_GRID,
          top: 60,
        },
        xAxis: {
          type: 'category',
          ...xName('日期'),
          data: labels,
          axisLabel: {
            interval: Math.max(1, Math.floor(labels.length / 12)),
          },
        },
        yAxis: [
          {
            type: 'value',
            ...yName('每日新增 (人)'),
            splitLine: {
              lineStyle: { color: '#f0f4f1' },
            },
          },
          {
            type: 'value',
            ...yName('累计 (人)'),
            splitLine: { show: false },
          },
        ],
        series: [
          {
            name: '每日新增',
            type: 'bar',
            data: rows.map((row) => row.new_users),
            itemStyle: {
              color: 'rgba(82,183,136,.75)',
              borderRadius: [3, 3, 0, 0],
            },
            barMaxWidth: 10,
          },
          {
            name: '累计',
            type: 'line',
            yAxisIndex: 1,
            data: rows.map((row) => row.cumulative),
            smooth: true,
            lineStyle: {
              color: '#6366f1',
              width: 2.5,
            },
            symbol: 'none',
          },
        ],
      }

      const columns: TableColumn[] = [
        { key: 'date', title: '日期' },
        { key: 'new_users', title: '新增', align: 'right' },
        {
          key: 'cumulative',
          title: '累计',
          align: 'right',
          render: (value) => (value as number).toLocaleString(),
        },
      ]

      return {
        chartOption,
        columns,
        rows: [...rows].reverse() as unknown as Record<string, unknown>[],
      }
    },
  })
}

function openGenderDetail() {
  open({
    title: '按性别 · 客户明细',
    subtitle: '默认展示男性客户',
    load: async () => {
      const response = await api.getCustomersList(1, 10000, {
        gender: 'male',
      })
      const list = response?.data ?? []

      const chartOption: EChartsOption = {
        tooltip: {
          trigger: 'item',
          ...TOOLTIP_BASE,
          formatter: (payload: unknown) =>
            `${getTooltipName(payload)}: ${getTooltipValue(payload)} (${getTooltipPercent(payload)}%)`,
        },
        legend: { top: 0 },
        series: [
          {
            type: 'pie',
            radius: ['40%', '70%'],
            data: genderData.value.map((item) => ({
              name: item.gender === 'male' ? '男性' : '女性',
              value: item.count,
              itemStyle: {
                color: item.gender === 'male' ? '#52b788' : '#b7e4c7',
              },
            })),
            label: {
              show: true,
              formatter: '{b}\n{d}%',
            },
          },
        ],
      }

      return {
        chartOption,
        columns: CUSTOMER_COLS,
        rows: list,
      }
    },
  })
}

function openProvinceDetail() {
  open({
    title: '省份用户分布 · 中国地图',
    subtitle: '颜色深浅代表用户数量',
    load: async () => {
      await ensureChinaMap()
      const response = await api.getUsersByProvince()
      const data = (response?.data ?? []) as Array<{
        province: string
        count: number
      }>

      const total = data.reduce((sum, item) => sum + item.count, 0) || 1
      const max = Math.max(1, ...data.map((item) => item.count))

      const chartOption: EChartsOption = {
        tooltip: {
          trigger: 'item',
          ...TOOLTIP_BASE,
          formatter: (payload: unknown) =>
            `${getTooltipName(payload)}: ${getTooltipDataValue(payload)} 人`,
        },
        visualMap: {
          right: 24,
          bottom: 24,
          min: 0,
          max,
          text: ['多', '少'],
          inRange: {
            color: ['#f0fdf4', '#74c69d', '#2d6a4f'],
          },
          calculable: true,
        },
        series: [
          {
            type: 'map',
            map: 'china',
            roam: true,
            zoom: 1,
            layoutCenter: ['50%', '50%'],
            layoutSize: '95%',
            label: { show: true, fontSize: 11 },
            emphasis: {
              label: {
                show: true,
                fontSize: 13,
                fontWeight: 700,
              },
              itemStyle: {
                areaColor: '#52b788',
              },
            },
            itemStyle: {
              borderColor: '#fff',
              borderWidth: 0.5,
            },
            data: data.map((item) => ({
              name: toFullProvinceName(item.province),
              value: item.count,
            })),
          },
        ],
      }

      const columns: TableColumn[] = [
        { key: 'province', title: '省份' },
        {
          key: 'count',
          title: '用户数',
          align: 'right',
          render: (value) => (value as number).toLocaleString(),
        },
        {
          key: 'pct',
          title: '占比',
          align: 'right',
          render: (_, row) =>
            `${((((row as { count: number }).count) / total) * 100).toFixed(1)}%`,
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

function openAgeDetail() {
  const ageOptions =
    ageData.value.length > 0
      ? ageData.value.map((item) => ({
          label: `${item.age_group} 岁`,
          value: item.age_group,
        }))
      : [{ label: '25-34 岁', value: '25-34' }]

  const defaultAge =
    ageOptions.find((item) => item.value === '25-34')?.value ??
    ageOptions[0].value

  open({
    title: '按年龄段 · 客户明细',
    subtitle: '切换年龄段查看对应客户',
    filters: [
      {
        key: 'age_group',
        label: '年龄段',
        options: ageOptions,
        default: defaultAge,
      },
    ],
    load: async (selected) => {
      const ageGroup = selected.age_group || defaultAge
      const response = await api.getCustomersList(1, 10000, {
        age_group: ageGroup,
      })
      const list = response?.data ?? []

      const chartOption: EChartsOption = {
        tooltip: {
          trigger: 'axis',
          ...TOOLTIP_BASE,
        },
        grid: AXIS_GRID,
        xAxis: {
          type: 'category',
          ...xName('年龄段'),
          data: ageData.value.map((item) => item.age_group),
        },
        yAxis: {
          type: 'value',
          ...yName('用户数 (人)'),
          splitLine: {
            lineStyle: { color: '#f0f4f1' },
          },
          axisLabel: {
            formatter: (value: number) => `${value}人`,
          },
        },
        series: [
          {
            type: 'bar',
            data: ageData.value.map((item, index) => ({
              value: item.count,
              itemStyle: {
                color:
                  item.age_group === ageGroup
                    ? '#2d6a4f'
                    : `rgba(82,183,136,${1 - index * 0.15})`,
              },
            })),
            barMaxWidth: 60,
            itemStyle: { borderRadius: [4, 4, 0, 0] },
          },
        ],
      }

      return {
        chartOption,
        columns: CUSTOMER_COLS,
        rows: list,
      }
    },
  })
}

const newOldOpt = computed<EChartsOption>(() => ({
  tooltip: {
    trigger: 'item',
    formatter: (payload: unknown) =>
      `${getTooltipName(payload)}: ${getTooltipValue(payload).toFixed(1)}%`,
  },
  series: [
    {
      type: 'pie',
      radius: ['55%', '78%'],
      avoidLabelOverlap: true,
      data: [
        {
          name: '新客',
          value: newPct.value,
          itemStyle: { color: '#74c69d' },
        },
        {
          name: '老客',
          value: 100 - newPct.value,
          itemStyle: { color: '#2d6a4f' },
        },
      ],
      label: {
        show: true,
        position: 'inside',
        formatter: '{b} {d}%',
        fontSize: 11,
        fontWeight: 400,
        color: '#000',
      },
      labelLine: { show: false },
      emphasis: {
        scale: true,
        scaleSize: 4,
        label: { fontSize: 13 },
      },
    },
  ],
}))

const genderOpt = computed<EChartsOption>(() => ({
  tooltip: {
    trigger: 'item',
    formatter: (payload: unknown) =>
      `${getTooltipName(payload)}: ${getTooltipValue(payload).toLocaleString()} (${getTooltipPercent(payload)}%)`,
  },
  series: [
    {
      type: 'pie',
      radius: ['55%', '78%'],
      avoidLabelOverlap: true,
      data: genderData.value.map((item) => ({
        name: item.gender === 'male' ? '男性' : '女性',
        value: item.count,
        itemStyle: {
          color: item.gender === 'male' ? '#52b788' : '#b7e4c7',
        },
      })),
      label: {
        show: true,
        position: 'inside',
        formatter: '{b} {d}%',
        fontSize: 11,
        fontWeight: 400,
        color: '#000',
      },
      labelLine: { show: false },
      emphasis: {
        scale: true,
        scaleSize: 4,
        label: { fontSize: 13 },
      },
    },
  ],
}))

const regOpt = computed<EChartsOption>(() => {
  const labels = growthData.value.map((item) => {
    const [, month, day] = item.date.split('-')
    return `${parseInt(month)}/${parseInt(day)}`
  })

  return {
    tooltip: {
      trigger: 'axis',
      ...TOOLTIP_BASE,
    },
    grid: AXIS_GRID,
    xAxis: {
      type: 'category',
      ...xName('日期'),
      data: labels,
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: {
        interval: Math.max(1, Math.floor(labels.length / 6)),
      },
    },
    yAxis: {
      type: 'value',
      ...yName('新增用户 (人)'),
      splitLine: {
        lineStyle: { color: '#f0f4f1' },
      },
      axisLabel: {
        formatter: (value: number) => `${value}人`,
      },
    },
    series: [
      {
        type: 'line',
        data: growthData.value.map((item) => item.new_users),
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
    ],
  }
})

const ageOpt = computed<EChartsOption>(() => ({
  tooltip: {
    trigger: 'axis',
    ...TOOLTIP_BASE,
  },
  grid: AXIS_GRID,
  xAxis: {
    type: 'category',
    ...xName('年龄段'),
    data: ageData.value.map((item) => item.age_group),
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: { show: false },
  },
  yAxis: {
    type: 'value',
    ...yName('用户数 (人)'),
    splitLine: {
      lineStyle: { color: '#f0f4f1' },
    },
    axisLabel: {
      formatter: (value: number) => `${value}人`,
    },
  },
  series: [
    {
      type: 'bar',
      data: ageData.value.map((item, index) => ({
        value: item.count,
        itemStyle: {
          color: `rgba(82,183,136,${1 - index * 0.15})`,
        },
      })),
      barMaxWidth: 40,
      itemStyle: { borderRadius: [4, 4, 0, 0] },
    },
  ],
}))

const provinceOpt = computed<EChartsOption>(() => {
  if (!mapReady.value) {
    return { series: [] }
  }

  const max = Math.max(1, ...provinceData.value.map((item) => item.count))

  return {
    tooltip: {
      trigger: 'item',
      ...TOOLTIP_BASE,
      formatter: (payload: unknown) =>
        `${getTooltipName(payload)}: ${getTooltipDataValue(payload).toLocaleString()} 人`,
    },
    visualMap: {
      right: 12,
      bottom: 12,
      min: 0,
      max,
      text: ['多', '少'],
      inRange: {
        color: ['#f0fdf4', '#74c69d', '#2d6a4f'],
      },
      calculable: true,
      textStyle: {
        fontSize: 11,
        color: 'var(--text2)',
      },
    },
    series: [
      {
        type: 'map',
        map: 'china',
        roam: true,
        zoom: 1,
        layoutCenter: ['50%', '50%'],
        layoutSize: '92%',
        label: { show: false },
        emphasis: {
          label: {
            show: true,
            fontSize: 12,
            fontWeight: 700,
          },
          itemStyle: {
            areaColor: '#52b788',
          },
        },
        itemStyle: {
          borderColor: '#fff',
          borderWidth: 0.5,
        },
        data: provinceData.value.map((item) => ({
          name: toFullProvinceName(item.province),
          value: item.count,
        })),
      },
    ],
  }
})

const provinceCols: TableColumn[] = [
  {
    key: 'name',
    title: '省份',
    render: (_, row, index) =>
      h(
        'span',
        {
          style: {
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          },
        },
        [
          h(
            'span',
            {
              style: {
                width: '22px',
                height: '22px',
                borderRadius: '6px',
                fontSize: '12px',
                fontWeight: 800,
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                background:
                  index < 3
                    ? ['#fef9c3', '#f1f5f0', '#ffedd5'][index]
                    : 'var(--bg)',
                color:
                  index < 3
                    ? ['#ca8a04', '#6b7280', '#ea580c'][index]
                    : 'var(--text3)',
              },
            },
            index + 1,
          ),
          (row as { name: string }).name,
        ],
      ),
  },
  {
    key: 'users',
    title: '用户数量',
    align: 'right',
    render: (value) => (value as number).toLocaleString(),
  },
  {
    key: 'pct',
    title: '占比',
    align: 'right',
    render: (value) =>
      h(
        'div',
        {
          style: {
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            justifyContent: 'flex-end',
          },
        },
        [
          h(
            'div',
            {
              style: {
                width: '80px',
                height: '6px',
                borderRadius: '3px',
                background: 'var(--border)',
                overflow: 'hidden',
              },
            },
            [
              h('div', {
                style: {
                  width: `${((value as number) / maxPct.value) * 100}%`,
                  height: '100%',
                  background: 'var(--green)',
                  borderRadius: '3px',
                },
              }),
            ],
          ),
          h(
            'span',
            {
              style: {
                minWidth: '40px',
                fontSize: '12px',
                fontWeight: 700,
                textAlign: 'right',
              },
            },
            `${value}%`,
          ),
        ],
      ),
  },
]
</script>

<style scoped>
.grid-3 {
  display: grid;
  grid-template-columns: 220px 1fr 220px;
  gap: 16px;
}

.pie-stack {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.legend-block {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.grid-map-side {
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  align-items: stretch;
  gap: 16px;
}

.side-col {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
}

.side-col > * {
  flex: 1 1 0;
  min-height: 0;
}

.province-scroll {
  max-height: 240px;
  overflow-y: auto;
}
</style>
