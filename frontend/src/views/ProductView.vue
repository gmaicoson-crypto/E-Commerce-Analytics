<template>
  <div class="fade-in">
    <PageHeader
      title="商品分析"
      subtitle="商品销量、库存及趋势分析"
    />

    <div class="kpi-row mb16">
      <KpiCard
        title="总商品数"
        :value="overviewKpi.total_products.toLocaleString()"
        icon="products"
        icon-bg="#dcfce7"
      />
      <KpiCard
        title="在售商品"
        :value="overviewKpi.on_sale.toLocaleString()"
        icon="checkCircle"
        icon-bg="#dbeafe"
      />
      <KpiCard
        title="低库存预警"
        :value="overviewKpi.low_stock_count.toLocaleString()"
        icon="alertCircle"
        icon-bg="#fee2e2"
      />
      <KpiCard
        title="总库存价值"
        :value="fmtMoneyCN(overviewKpi.total_inventory_value, { prefix: '' })"
        prefix="¥"
        icon="finance"
        icon-bg="#ede9fe"
      />
    </div>

    <AppCard
      title="商品管理"
      subtitle="维护商品基础信息、价格、库存和上下架状态"
      class="mb16"
    >
      <template #extra>
        <div class="manage-actions">
          <button class="mg-btn ghost" @click="loadManagedProducts()">
            刷新
          </button>
          <button class="mg-btn primary" @click="openProductModal()">
            新增商品
          </button>
        </div>
      </template>

      <div class="manage-toolbar">
        <input
          v-model.trim="productFilters.keyword"
          class="mg-input"
          placeholder="搜索商品名称"
          @keyup.enter="loadManagedProducts(1)"
        />
        <ThemedSelect
          v-model="productFilters.category"
          :options="productCategoryFilterOpts"
          :min-width="120"
          @change="loadManagedProducts(1)"
        />
        <ThemedSelect
          v-model="productFilters.status"
          :options="productStatusFilterOpts"
          :min-width="120"
          @change="loadManagedProducts(1)"
        />
        <button class="mg-btn ghost" @click="resetProductFilters">
          重置
        </button>
      </div>

      <DataTable
        :columns="(managedProductCols as unknown as TableColumn<Record<string, unknown>>[])"
        :data="(managedProducts as unknown as Record<string,unknown>[])"
        empty-text="暂无商品"
      />

      <div class="manage-pager">
        <span>共 {{ productPage.total }} 条 · 第 {{ productPage.page }} / {{ Math.max(productPage.total_pages, 1) }} 页</span>
        <button
          class="mg-btn ghost"
          :disabled="productPage.page <= 1"
          @click="loadManagedProducts(productPage.page - 1)"
        >
          上一页
        </button>
        <button
          class="mg-btn ghost"
          :disabled="productPage.page >= productPage.total_pages"
          @click="loadManagedProducts(productPage.page + 1)"
        >
          下一页
        </button>
      </div>

      <p v-if="productManageError" class="manage-error">
        {{ productManageError }}
      </p>
    </AppCard>

    <div class="grid-equal-2 mb16">
      <AppCard title="品类销量占比" class="equal-card">
        <template #extra>
          <button class="ico-btn" title="展开详情" @click="openCategoryDetail">
            <AppIcon name="maximize" :size="14" color="var(--text2)" />
          </button>
        </template>
        <EChartBox :option="catOpt" :height="240" />
        <div class="legend-list">
          <LegendItem
            v-for="(c, i) in catData"
            :key="c.name"
            :color="PAL[i]"
            :label="c.name"
            :pct="c.pct"
          />
        </div>
      </AppCard>

      <AppCard
        title="品类每日 TOP5 商品"
        :subtitle="`${dailyTopDate} · ${dailyTopCategory}`"
        class="equal-card"
      >
        <template #extra>
          <div class="cat-daily-filters">
            <ThemedSelect
              v-model="dailyTopDate"
              :options="dateOpts"
              :min-width="120"
              @change="loadDailyTop"
            />
            <ThemedSelect
              v-model="dailyTopCategory"
              :options="categoryOpts"
              :min-width="84"
              @change="loadDailyTop"
            />
          </div>
        </template>
        <EChartBox :option="dailyTopOpt" :height="320" />
      </AppCard>
    </div>

    <AppCard
      title="TOP5 商品销量趋势"
      :subtitle="selectedProductTrend ? `${selectedProductTrend.product_name} · 近30天日销量` : '近30天日销量'"
      class="mb16"
    >
      <template #extra>
        <ThemedSelect
          v-model="selectedTrendPid"
          :options="trendProductOpts"
          :min-width="180"
        />
      </template>
      <EChartBox :option="trendOpt" :height="340" />
    </AppCard>

    <div class="grid-equal-2 mb16">
      <AppCard
        title="商品销量 TOP10"
        subtitle="近30天销售额排行"
        class="equal-card"
      >
        <div class="scroll-body">
          <DataTable
            :columns="top10Cols"
            :data="(top10 as Record<string,unknown>[])"
          />
        </div>
      </AppCard>

      <AppCard
        title="库存预警明细"
        subtitle="库存低于预警阈值的商品"
        class="equal-card"
      >
        <template #extra>
          <AppBadge :label="`${inventory.length}条`" color="red" />
        </template>
        <div class="scroll-body">
          <DataTable
            :columns="invCols"
            :data="(inventory as Record<string,unknown>[])"
          />
        </div>
      </AppCard>
    </div>

    <AppCard title="商品列表 · 销售表现 TOP20">
      <template #extra>
        <button class="ico-btn" title="展开详情" @click="openProductList20Detail">
          <AppIcon name="maximize" :size="14" color="var(--text2)" />
        </button>
      </template>
      <DataTable
        :columns="listCols"
        :data="(productList as Record<string,unknown>[])"
      />
    </AppCard>

    <div
      v-if="productModalOpen"
      class="modal-mask"
      @click.self="closeProductModal"
    >
      <div class="modal-card">
        <div class="modal-head">
          <h3>{{ editingProduct ? '编辑商品' : '新增商品' }}</h3>
          <button class="modal-x" @click="closeProductModal">
            ×
          </button>
        </div>

        <div class="modal-body">
          <label>
            商品名称
            <input v-model.trim="productForm.product_name" />
          </label>
          <label>
            品类
            <ThemedSelect
              v-model="productForm.category"
              :options="productCategoryEditOpts"
              min-width="100%"
            />
          </label>
          <label>
            状态
            <ThemedSelect
              v-model="productForm.status"
              :options="productStatusEditOpts"
              min-width="100%"
            />
          </label>
          <label>
            价格
            <input
              v-model.number="productForm.price"
              type="number"
              min="0"
              step="0.01"
            />
          </label>
          <label>
            成本
            <input
              v-model.number="productForm.cost"
              type="number"
              min="0"
              step="0.01"
            />
          </label>
          <label>
            库存
            <input
              v-model.number="productForm.stock"
              type="number"
              min="0"
              step="1"
            />
          </label>
          <label>
            预警阈值
            <input
              v-model.number="productForm.low_stock_threshold"
              type="number"
              min="0"
              step="1"
            />
          </label>
          <p v-if="productFormError" class="manage-error">
            {{ productFormError }}
          </p>
        </div>

        <div class="modal-foot">
          <button class="mg-btn ghost" @click="closeProductModal">
            取消
          </button>
          <button
            class="mg-btn primary"
            :disabled="productSaving"
            @click="saveProduct"
          >
            {{ productSaving ? '保存中' : '保存' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue'
import type { EChartsOption } from 'echarts'
import AppBadge from '@/components/common/AppBadge.vue'
import AppCard from '@/components/common/AppCard.vue'
import AppIcon from '@/components/common/AppIcon.vue'
import DataTable from '@/components/common/DataTable.vue'
import EChartBox from '@/components/common/EChartBox.vue'
import KpiCard from '@/components/common/KpiCard.vue'
import LegendItem from '@/components/common/LegendItem.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import ThemedSelect from '@/components/common/ThemedSelect.vue'
import { useChartDetail } from '@/composables/useChartDetail'
import { useDebouncedReload } from '@/composables/useEventStream'
import { api } from '@/services/api'
import type { LowStockProduct, ProductPerformance, TableColumn } from '@/types'
import {
  AXIS_GRID,
  CHART_PALETTE as PAL,
  TOOLTIP_BASE,
  fmtMoneyCN,
  xName,
  yName,
} from '@/utils/constants'

function tooltipName(payload: unknown): string {
  const name = (payload as { name?: unknown })?.name
  return typeof name === 'string' ? name : ''
}

function tooltipValue(payload: unknown): number {
  const value = (payload as { value?: unknown })?.value
  return typeof value === 'number' && Number.isFinite(value) ? value : 0
}

function tooltipPercent(payload: unknown): number {
  const percent = (payload as { percent?: unknown })?.percent
  return typeof percent === 'number' && Number.isFinite(percent) ? percent : 0
}

function tooltipArray(
  payload: unknown
): Array<{ name: string; value: number; data?: unknown }> {
  if (!Array.isArray(payload)) {
    return []
  }

  return payload.map((item) => ({
    name: tooltipName(item),
    value: tooltipValue(item),
    data: (item as { data?: unknown }).data,
  }))
}

function tooltipDataRecord(payload: unknown): Record<string, unknown> {
  const data = (payload as { data?: unknown })?.data
  return data && typeof data === 'object'
    ? (data as Record<string, unknown>)
    : {}
}

const performance = ref<ProductPerformance[]>([])
const lowStock = ref<LowStockProduct[]>([])
const categoryRaw = ref<{ category: string; count: number }[]>([])
const overviewKpi = ref({
  total_products: 0,
  on_sale: 0,
  off_sale: 0,
  low_stock_count: 0,
  total_stock: 0,
  total_inventory_value: 0,
})

interface TopTrendProduct {
  product_id: number
  product_name: string
  category: string | null
  total_qty: number
  daily: number[]
}
interface TopTrendResp {
  period_days: number
  dates: string[]
  products: TopTrendProduct[]
}

const topTrend = ref<TopTrendResp>({
  period_days: 30,
  dates: [],
  products: [],
})

const selectedTrendPid = ref<string>('')
const trendProductOpts = computed(() =>
  topTrend.value.products.map((p, i) => ({
    label: `TOP${i + 1} · ${p.product_name}`,
    value: String(p.product_id),
  }))
)
const selectedProductTrend = computed(() => {
  const pid = Number(selectedTrendPid.value)
  return (
    topTrend.value.products.find(p => p.product_id === pid) ??
    topTrend.value.products[0] ??
    null
  )
})

const CATEGORIES = ['服装', '电子', '食品', '家居', '美妆'] as const
const categoryOpts = CATEGORIES.map(c => ({ label: c, value: c }))
const productCategoryFilterOpts = [
  { label: '全部品类', value: '' },
  ...CATEGORIES.map(c => ({ label: c, value: c })),
]
const productCategoryEditOpts = CATEGORIES.map(c => ({ label: c, value: c }))
const productStatusFilterOpts = [
  { label: '全部状态', value: '' },
  { label: '在售', value: 'on_sale' },
  { label: '下架', value: 'off_sale' },
]
const productStatusEditOpts = [
  { label: '在售', value: 'on_sale' },
  { label: '下架', value: 'off_sale' },
]

interface ManagedProduct {
  id: number
  product_name: string
  category: string
  price: number
  cost: number
  stock: number
  low_stock_threshold: number
  status: string
  created_at?: string | null
}

interface ProductForm {
  product_name: string
  category: string
  price: number
  cost: number
  stock: number
  low_stock_threshold: number
  status: string
}

const managedProducts = ref<ManagedProduct[]>([])
const productFilters = ref({ keyword: '', category: '', status: '' })
const productPage = ref({
  page: 1,
  page_size: 10,
  total: 0,
  total_pages: 0,
})
const productManageError = ref('')
const productModalOpen = ref(false)
const productSaving = ref(false)
const productFormError = ref('')
const editingProduct = ref<ManagedProduct | null>(null)
const productForm = ref<ProductForm>({
  product_name: '',
  category: CATEGORIES[0],
  price: 99,
  cost: 50,
  stock: 100,
  low_stock_threshold: 10,
  status: 'on_sale',
})

const productFieldLabels: Record<keyof ProductForm, string> = {
  product_name: '商品名称',
  category: '品类',
  price: '价格',
  cost: '成本',
  stock: '库存',
  low_stock_threshold: '预警阈值',
  status: '状态',
}

function productStatusLabel(value: string) {
  return value === 'on_sale' ? '在售' : value === 'off_sale' ? '下架' : value
}

function productErrorMessage(error: unknown, fallback: string) {
  const message = error instanceof Error ? error.message : fallback
  if (message.includes('Product is used by orders'))
    return '该商品已被订单引用，无法删除'
  if (message.includes('Product not found')) return '商品不存在'
  if (message.includes('Invalid category')) return '品类无效'
  if (message.includes('Invalid status')) return '状态无效'
  return message || fallback
}

async function loadManagedProducts(page = productPage.value.page) {
  productManageError.value = ''
  try {
    const result = await api.getManagedProducts(page, productPage.value.page_size, {
      keyword: productFilters.value.keyword || undefined,
      category: productFilters.value.category || undefined,
      status: productFilters.value.status || undefined,
    })
    managedProducts.value = result?.data ?? []
    productPage.value = result?.pagination ?? {
      page,
      page_size: productPage.value.page_size,
      total: 0,
      total_pages: 0,
    }
  } catch (e) {
    productManageError.value = productErrorMessage(e, '加载商品失败')
    managedProducts.value = []
  }
}

function resetProductFilters() {
  productFilters.value = { keyword: '', category: '', status: '' }
  loadManagedProducts(1)
}

function openProductModal(row?: ManagedProduct) {
  editingProduct.value = row ?? null
  productFormError.value = ''
  productForm.value = row
    ? {
        product_name: row.product_name,
        category: row.category,
        price: row.price,
        cost: row.cost,
        stock: row.stock,
        low_stock_threshold: row.low_stock_threshold,
        status: row.status,
      }
    : {
        product_name: '',
        category: CATEGORIES[0],
        price: 99,
        cost: 50,
        stock: 100,
        low_stock_threshold: 10,
        status: 'on_sale',
      }
  productModalOpen.value = true
}

function closeProductModal() {
  productModalOpen.value = false
  editingProduct.value = null
  productFormError.value = ''
}

function validateProductForm() {
  const form = productForm.value
  if (!form.product_name.trim()) return '请输入商品名称'
  if (!form.category) return '请选择品类'
  if (!form.status) return '请选择状态'
  for (const key of ['price', 'cost', 'stock', 'low_stock_threshold'] as const) {
    if (
      !Number.isFinite(Number(form[key])) ||
      Number(form[key]) < 0
    ) {
      return `${productFieldLabels[key]}必须是非负数`
    }
  }
  return ''
}

async function saveProduct() {
  const err = validateProductForm()
  if (err) {
    productFormError.value = err
    return
  }
  productSaving.value = true
  productFormError.value = ''
  const wasEditing = Boolean(editingProduct.value)
  try {
    if (editingProduct.value) {
      await api.updateManagedProduct(
        editingProduct.value.id,
        productForm.value
      )
    } else {
      await api.createManagedProduct(productForm.value)
    }
    closeProductModal()
    await Promise.all([
      loadManagedProducts(wasEditing ? productPage.value.page : 1),
      loadData(),
      loadDailyTop(),
    ])
  } catch (e) {
    productFormError.value = productErrorMessage(e, '保存商品失败')
  } finally {
    productSaving.value = false
  }
}

async function deleteManagedProduct(row: ManagedProduct) {
  if (!window.confirm(`确定删除商品「${row.product_name}」吗？`)) return
  productManageError.value = ''
  try {
    await api.deleteManagedProduct(row.id)
    await Promise.all([
      loadManagedProducts(productPage.value.page),
      loadData(),
      loadDailyTop(),
    ])
  } catch (e) {
    productManageError.value = productErrorMessage(e, '删除商品失败')
  }
}

const managedProductCols: TableColumn<ManagedProduct>[] = [
  { key: 'product_name', title: '商品名称', wrap: true },
  { key: 'category', title: '品类' },
  {
    key: 'price',
    title: '价格',
    align: 'right',
    render: v => fmtMoneyCN(v as number),
  },
  {
    key: 'cost',
    title: '成本',
    align: 'right',
    render: v => fmtMoneyCN(v as number),
  },
  { key: 'stock', title: '库存', align: 'right' },
  { key: 'low_stock_threshold', title: '预警阈值', align: 'right' },
  {
    key: 'status',
    title: '状态',
    render: v => badge(productStatusLabel(v as string), '在售', '下架'),
  },
  {
    key: 'actions',
    title: '操作',
    align: 'center',
    render: (_, row) =>
      h(
        'div',
        {
          style: {
            display: 'flex',
            justifyContent: 'center',
            gap: '8px',
            whiteSpace: 'nowrap',
          },
        },
        [
          h(
            'button',
            {
              style: {
                height: '28px',
                padding: '0 9px',
                borderRadius: '7px',
                border: '1px solid var(--border)',
                background: '#fff',
                color: 'var(--text2)',
                fontSize: '12px',
                fontWeight: 800,
                cursor: 'pointer',
              },
              onClick: () => openProductModal(row as ManagedProduct),
            },
            '编辑'
          ),
          h(
            'button',
            {
              style: {
                height: '28px',
                padding: '0 9px',
                borderRadius: '7px',
                border: '1px solid #fecdd3',
                background: '#fff1f2',
                color: '#dc2626',
                fontSize: '12px',
                fontWeight: 800,
                cursor: 'pointer',
              },
              onClick: () => deleteManagedProduct(row as ManagedProduct),
            },
            '删除'
          ),
        ]
      ),
  },
]

const todayISO = new Date().toISOString().slice(0, 10)
const dailyTopDate = ref(todayISO)
const dailyTopCategory = ref<string>(CATEGORIES[0])
const dailyTopData = ref<
  { product_name: string; quantity: number; sales: number }[]
>([])

const dateOpts = computed(() => {
  const out: { label: string; value: string }[] = []
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

async function loadDailyTop() {
  try {
    const r = await api.getCategoryDailyTop(
      dailyTopDate.value,
      dailyTopCategory.value,
      5
    )
    dailyTopData.value = (r?.data ?? []) as {
      product_name: string
      quantity: number
      sales: number
    }[]
  } catch (e) {
    console.error('[ProductView] loadDailyTop failed', e)
    dailyTopData.value = []
  }
}

const top10 = computed(() =>
  performance.value.slice(0, 10).map((p, i) => ({
    rank: i + 1,
    name: p.product_name,
    category: p.category,
    qty: p.quantity_sold,
    amount: p.sales,
  }))
)

const inventory = computed(() =>
  lowStock.value.map((p) => ({
    name: p.product_name,
    category: p.category,
    stock: p.stock,
    threshold: p.low_stock_threshold,
    status: p.stock < p.low_stock_threshold / 2 ? '严重' : '预警',
  }))
)

const productList = computed(() =>
  performance.value.slice(0, 20).map((p) => ({
    name: p.product_name,
    category: p.category,
    qty: p.quantity_sold,
    price: p.price,
    sales: p.sales,
    profit_margin: p.profit_margin,
  }))
)

const catData = computed(() => {
  const total = categoryRaw.value.reduce((a, c) => a + c.count, 0) || 1
  return categoryRaw.value
    .map((c) => ({
      name: c.category,
      pct: Math.round((c.count / total) * 100),
    }))
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
    lowStock.value = low?.data ?? []
    categoryRaw.value = (byCat ?? []) as { category: string; count: number }[]
    if (ovw) overviewKpi.value = ovw
    topTrend.value = (trend as TopTrendResp) ?? {
      period_days: 30,
      dates: [],
      products: [],
    }
    const first = topTrend.value.products[0]
    if (
      first &&
      !topTrend.value.products.some(
        p => String(p.product_id) === selectedTrendPid.value
      )
    ) {
      selectedTrendPid.value = String(first.product_id)
    }
  } catch (e) {
    console.error('[ProductView] load failed', e)
  }
}

onMounted(() => {
  loadData()
  loadDailyTop()
  loadManagedProducts(1)
})
useDebouncedReload(['product', 'order'], () => {
  loadData()
  loadDailyTop()
  loadManagedProducts(productPage.value.page)
})

const { open } = useChartDetail()

function openCategoryDetail() {
  open({
    title: '品类商品分布',
    subtitle: '各品类商品数量 / 在售 / 库存 / 均价',
    load: async () => {
      const data = (await api.getProductsByCategory()) as {
        category: string
        count: number
        on_sale: number
        avg_price: number
        avg_cost: number
        total_stock: number
      }[]
      const totalCount = data.reduce((a, c) => a + c.count, 0) || 1
      const chartOption: EChartsOption = {
        tooltip: {
          trigger: 'item',
          ...TOOLTIP_BASE,
          formatter: (payload: unknown) =>
            `${tooltipName(payload)}: ${tooltipValue(payload)} 件 (${tooltipPercent(payload)}%)`,
        },
        legend: { top: 0 },
        series: [
          {
            type: 'pie',
            radius: ['40%', '70%'],
            data: data.map((c, i) => ({
              name: c.category,
              value: c.count,
              itemStyle: { color: PAL[i % PAL.length] },
            })),
            label: { show: true, formatter: '{b}\n{d}%' },
          },
        ],
      }
      const cols: TableColumn[] = [
        { key: 'category', title: '品类' },
        { key: 'count', title: '商品数', align: 'right' },
        { key: 'on_sale', title: '在售', align: 'right' },
        {
          key: 'total_stock',
          title: '总库存',
          align: 'right',
          render: (v) => (v as number).toLocaleString(),
        },
        {
          key: 'avg_price',
          title: '均价',
          align: 'right',
          render: (v) => `¥${(v as number).toFixed(2)}`,
        },
        {
          key: 'avg_cost',
          title: '均成本',
          align: 'right',
          render: (v) => `¥${(v as number).toFixed(2)}`,
        },
        {
          key: 'pct',
          title: '占比',
          align: 'right',
          render: (_, row) => {
            const r = row as { count: number }
            return `${((r.count / totalCount) * 100).toFixed(1)}%`
          },
        },
      ]
      return { chartOption, columns: cols, rows: data as unknown as Record<string, unknown>[] }
    },
  })
}

function openProductList20Detail() {
  open({
    title: '商品列表 · 销售表现 TOP20 · 近 90 天',
    load: async () => {
      const r = await api.getProductsPerformance('90', 20)
      const rows = (r?.data ?? []) as ProductPerformance[]
      const chartOption: EChartsOption = {
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'shadow' },
          ...TOOLTIP_BASE,
          formatter: (payload: unknown) => {
            const items = tooltipArray(payload)
            return items[0] ? `${items[0].name}: ${fmtMoneyCN(items[0].value)}` : ''
          },
        },
        grid: AXIS_GRID,
        xAxis: {
          type: 'value',
          ...xName('销售额 (¥)'),
          splitLine: { lineStyle: { color: '#f0f4f1' } },
          axisLabel: { formatter: (v: number) => fmtMoneyCN(v, { wanDecimals: 0 }) },
        },
        yAxis: {
          type: 'category',
          ...yName('商品'),
          data: rows.map(p => p.product_name.slice(0, 16)).reverse(),
          axisLine: { show: false },
          axisTick: { show: false },
        },
        series: [
          {
            type: 'bar',
            data: rows.map(p => p.sales).reverse(),
            itemStyle: { color: 'rgba(82,183,136,.85)', borderRadius: [0, 4, 4, 0] },
            barMaxWidth: 16,
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
      const cols: TableColumn[] = [
        { key: 'rank', title: '排名', align: 'right' },
        { key: 'product_name', title: '商品名', wrap: true },
        { key: 'category', title: '品类' },
        {
          key: 'price',
          title: '售价',
          align: 'right',
          render: (v) => `¥${(v as number).toFixed(2)}`,
        },
        {
          key: 'quantity_sold',
          title: '销量',
          align: 'right',
          render: (v) => (v as number).toLocaleString(),
        },
        {
          key: 'sales',
          title: '销售额',
          align: 'right',
          render: (v) =>
            `¥${(v as number).toLocaleString(undefined, { maximumFractionDigits: 0 })}`,
        },
        {
          key: 'profit',
          title: '毛利',
          align: 'right',
          render: (v) =>
            `¥${(v as number).toLocaleString(undefined, { maximumFractionDigits: 0 })}`,
        },
        {
          key: 'profit_margin',
          title: '毛利率',
          align: 'right',
          render: (v) => `${(v as number).toFixed(1)}%`,
        },
      ]
      const tableRows = rows.map((r, i) => ({ rank: i + 1, ...r }))
      return { chartOption, columns: cols, rows: tableRows as unknown as Record<string, unknown>[] }
    },
  })
}

const badge = (v: string, ok: string, ng: string) =>
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
        background: v === ok ? '#dcfce7' : v === ng ? '#fee2e2' : '#fef9c3',
        color: v === ok ? '#15803d' : v === ng ? '#dc2626' : '#ca8a04',
      },
    },
    v,
  )

const top10Cols: TableColumn[] = [
  {
    key: 'rank',
    title: '排名',
    render: (v) => {
      const n = v as number
      const bg = n <= 3
        ? ['#fef9c3', '#f1f5f0', '#ffedd5'][n - 1]
        : 'var(--bg)'
      const color = n <= 3
        ? ['#ca8a04', '#6b7280', '#ea580c'][n - 1]
        : 'var(--text3)'
      return h(
        'span',
        {
          style: {
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '24px',
            height: '24px',
            borderRadius: '6px',
            fontSize: '12px',
            fontWeight: 800,
            background: bg,
            color,
          },
        },
        String(v),
      )
    },
  },
  { key: 'name', title: '商品名称', wrap: true },
  { key: 'category', title: '品类' },
  {
    key: 'qty',
    title: '销量',
    align: 'right',
    render: (v) => `${(v as number).toLocaleString()} 件`,
  },
  {
    key: 'amount',
    title: '销售额',
    align: 'right',
    render: (v) => fmtMoneyCN(v as number),
  },
]

const invCols: TableColumn[] = [
  { key: 'name', title: '商品名称', wrap: true },
  { key: 'category', title: '品类' },
  {
    key: 'stock',
    title: '当前库存',
    align: 'right',
    render: (v) =>
      h(
        'span',
        { style: { fontWeight: 800, color: (v as number) < 20 ? '#dc2626' : '#f59e0b' } },
        String(v),
      ),
  },
  { key: 'threshold', title: '预警阈值', align: 'right' },
  { key: 'status', title: '状态', render: (v) => badge(v as string, '', '严重') },
]

const listCols: TableColumn[] = [
  { key: 'name', title: '商品名称', wrap: true },
  { key: 'category', title: '品类' },
  {
    key: 'qty',
    title: '销售数量',
    align: 'right',
    render: (v) => (v as number).toLocaleString(),
  },
  {
    key: 'price',
    title: '售价',
    align: 'right',
    render: (v) => `¥${(v as number).toFixed(2)}`,
  },
  {
    key: 'sales',
    title: '销售额',
    align: 'right',
    render: (v) => fmtMoneyCN(v as number),
  },
  {
    key: 'profit_margin',
    title: '毛利率',
    align: 'right',
    render: (v) => `${(v as number).toFixed(1)}%`,
  },
]

const VIVID5 = ['#6366f1', '#f59e0b', '#ec4899', '#06b6d4', '#f97316']

const trendOpt = computed<EChartsOption>(() => {
  const p = selectedProductTrend.value
  const labels = topTrend.value.dates.map(d => d.slice(5))
  const idx = p
    ? topTrend.value.products.findIndex(x => x.product_id === p.product_id)
    : 0
  const color = VIVID5[(idx >= 0 ? idx : 0) % VIVID5.length]
  return {
    tooltip: {
      trigger: 'axis',
      ...TOOLTIP_BASE,
      formatter: (params: unknown) => {
        const arr = tooltipArray(params)
        const v = arr[0]?.value ?? 0
        return `${arr[0]?.name ?? ''}<br>${p?.product_name ?? ''}: ${v} 件`
      },
    },
    grid: AXIS_GRID,
    xAxis: {
      type: 'category',
      ...xName('日期'),
      data: labels,
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { interval: Math.max(1, Math.floor(labels.length / 10)) },
    },
    yAxis: {
      type: 'value',
      ...yName('日销量 (件)'),
      minInterval: 1,
      splitLine: { lineStyle: { color: '#f0f4f1' } },
      axisLabel: { formatter: (v: number) => `${v}件` },
    },
    series: [
      {
        type: 'line',
        smooth: true,
        data: p?.daily ?? [],
        lineStyle: { color, width: 2.5 },
        areaStyle: { color: `${color}20` },
        symbol: 'circle',
        symbolSize: 4,
        itemStyle: { color },
      },
    ],
  }
})

const dailyTopOpt = computed<EChartsOption>(() => {
  const rows = [...dailyTopData.value].reverse()
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      ...TOOLTIP_BASE,
      formatter: (payload: unknown) => {
        const item = tooltipArray(payload)[0]
        const data = tooltipDataRecord(item)
        const name = String(data.name ?? item?.name ?? '')
        const quantity = typeof data.quantity === 'number' ? data.quantity : 0
        const sales = typeof data.sales === 'number' ? data.sales : 0
        return `${name}<br>销量: ${quantity} 件<br>销售额: ${fmtMoneyCN(sales)}`
      },
    },
    grid: { ...AXIS_GRID, left: 90, right: 60 },
    xAxis: {
      type: 'value',
      ...xName('销售额 (¥)'),
      splitLine: { lineStyle: { color: '#f0f4f1' } },
      axisLabel: { formatter: (v: number) => fmtMoneyCN(v, { wanDecimals: 0 }) },
    },
    yAxis: {
      type: 'category',
      ...yName('商品'),
      data: rows.map(r => r.product_name.slice(0, 16)),
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: [
      {
        type: 'bar',
        data: rows.map(r => ({
          name: r.product_name,
          value: r.sales,
          quantity: r.quantity,
          sales: r.sales,
        })),
        itemStyle: { color: 'rgba(82,183,136,.85)', borderRadius: [0, 4, 4, 0] },
        barMaxWidth: 22,
        label: {
          show: true,
          position: 'right',
          formatter: (payload: unknown) => {
            const data = tooltipDataRecord(payload)
            const quantity = typeof data.quantity === 'number' ? data.quantity : 0
            const sales = typeof data.sales === 'number' ? data.sales : 0
            return `${quantity}件 · ${fmtMoneyCN(sales, { wanDecimals: 0 })}`
          },
          fontSize: 11,
          color: 'var(--text2)',
        },
      },
    ],
  }
})

const catOpt = computed<EChartsOption>(() => ({
  tooltip: {
    trigger: 'item',
    ...TOOLTIP_BASE,
    formatter: (payload: unknown) =>
      `${tooltipName(payload)}: ${tooltipValue(payload)}%`,
  },
  series: [
    {
      type: 'pie',
      radius: ['45%', '72%'],
      avoidLabelOverlap: true,
      data: catData.value.map((c, i) => ({
        name: c.name,
        value: c.pct,
        itemStyle: { color: PAL[i] },
      })),
      label: {
        show: true,
        formatter: '{b}\n{c}%',
        fontSize: 11,
        fontWeight: 700,
        color: 'inherit',
      },
      labelLine: { show: true, length: 8, length2: 8, lineStyle: { color: 'inherit' } },
      emphasis: { scale: true, scaleSize: 6, label: { fontSize: 13 } },
    },
  ],
}))
</script>

<style scoped>
.equal-card {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.equal-card :deep(.card) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.equal-card :deep(.card-body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.legend-list {
  margin-top: 14px;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 6px 18px;
}

.scroll-body {
  flex: 1;
  max-height: 440px;
  overflow-y: auto;
}

.cat-daily-filters {
  display: flex;
  gap: 8px;
  align-items: center;
}

.manage-actions,
.manage-toolbar,
.manage-pager,
.row-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.manage-toolbar {
  margin-bottom: 12px;
}

.manage-pager {
  justify-content: flex-end;
  margin-top: 12px;
  color: var(--text2);
  font-size: 13px;
}

.mg-input {
  height: 34px;
  min-width: 200px;
  border: 1px solid var(--border);
  border-radius: 7px;
  padding: 0 10px;
  color: var(--text1);
  background: #fff;
}

.mg-input:focus {
  outline: none;
  border-color: var(--green);
  box-shadow: 0 0 0 3px var(--green-50);
}

.mg-btn {
  height: 32px;
  padding: 0 12px;
  border-radius: 7px;
  border: 1px solid var(--border);
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
  background: #fff;
  color: var(--text2);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  white-space: nowrap;
}

.mg-btn.small {
  height: 28px;
  padding: 0 9px;
}

.mg-btn.primary {
  background: var(--green);
  border-color: var(--green);
  color: #fff;
}

.mg-btn.ghost:hover {
  background: var(--green-50);
  color: var(--green-dark);
}

.mg-btn.danger {
  background: #fff1f2;
  border-color: #fecdd3;
  color: #dc2626;
}

.mg-btn.danger:hover {
  background: #fee2e2;
}

.mg-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.manage-error {
  margin: 10px 0 0;
  color: #dc2626;
  font-size: 13px;
  font-weight: 700;
}

.modal-mask {
  position: fixed;
  inset: 0;
  z-index: 240;
  background: rgba(17, 24, 39, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.modal-card {
  width: 460px;
  max-width: 100%;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 18px 56px rgba(0, 0, 0, 0.22);
  overflow: hidden;
}

.modal-head,
.modal-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border);
}

.modal-foot {
  justify-content: flex-end;
  border-top: 1px solid var(--border);
  border-bottom: none;
}

.modal-head h3 {
  margin: 0;
  font-size: 16px;
  color: var(--text1);
}

.modal-x {
  border: none;
  background: transparent;
  font-size: 22px;
  line-height: 1;
  color: var(--text3);
  cursor: pointer;
}

.modal-body {
  padding: 16px 18px;
  display: grid;
  gap: 10px;
}

.modal-body label {
  display: grid;
  grid-template-columns: 96px 1fr;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  font-weight: 700;
  color: var(--text2);
}

.modal-body input,
.modal-body select {
  height: 34px;
  border: 1px solid var(--border);
  border-radius: 7px;
  padding: 0 10px;
  color: var(--text1);
  background: #fff;
}

.modal-body :deep(.ts-wrap),
.modal-body :deep(.ts-trigger) {
  width: 100%;
}
</style>
