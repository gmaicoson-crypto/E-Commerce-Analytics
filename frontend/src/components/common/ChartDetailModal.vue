<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="current" class="overlay" @click.self="close" @keydown.esc="close" tabindex="-1">
        <div class="modal">
          <header class="head">
            <div class="titles">
              <h2>{{ current.title }}</h2>
              <p v-if="current.subtitle">{{ current.subtitle }}</p>
            </div>
            <button class="close-btn" @click="close" aria-label="关闭">
              <AppIcon name="close" :size="20" color="var(--text2)" />
            </button>
          </header>

          <div class="body">
            <section class="chart">
              <div v-if="loading" class="state">加载中...</div>
              <div v-else-if="error" class="state err">{{ error }}</div>
              <EChartBox v-else-if="chartOption" :option="chartOption" :height="chartHeight" />
            </section>
            <section class="table">
              <div v-if="loading" class="state">加载中...</div>
              <DataTable
                v-else
                :columns="columns"
                :data="(rows as Record<string,unknown>[])"
                :pagination="true"
                :page-size="15"
              />
            </section>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount, computed } from 'vue'
import type { EChartsOption } from 'echarts'
import { useChartDetail } from '@/composables/useChartDetail'
import AppIcon from '@/components/common/AppIcon.vue'
import EChartBox from '@/components/common/EChartBox.vue'
import DataTable from '@/components/common/DataTable.vue'
import type { TableColumn } from '@/types'

const { current, close } = useChartDetail()

const loading = ref(false)
const error = ref('')
const chartOption = ref<EChartsOption | null>(null)
const columns = ref<TableColumn[]>([])
const rows = ref<Record<string, unknown>[]>([])

const chartHeight = computed(() => Math.round(window.innerHeight * 0.78))

async function loadDetail() {
  if (!current.value) return
  loading.value = true
  error.value = ''
  chartOption.value = null
  columns.value = []
  rows.value = []
  try {
    const res = await current.value.load()
    chartOption.value = res.chartOption
    columns.value = res.columns
    rows.value = res.rows
  } catch (e) {
    error.value = (e as Error).message || '加载失败'
    console.error('[ChartDetailModal] load failed', e)
  } finally {
    loading.value = false
  }
}

watch(current, (val) => {
  if (val) {
    loadDetail()
    document.body.style.overflow = 'hidden'
  } else {
    document.body.style.overflow = ''
  }
})

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && current.value) close()
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  document.body.style.overflow = ''
})
</script>

<style scoped>
.overlay { position:fixed; inset:0; background:rgba(15,23,28,.55); display:flex; align-items:center; justify-content:center; z-index:9999; padding:12px; }
.modal { background:var(--card,#fff); border-radius:16px; width:96vw; height:94vh; box-shadow:0 24px 80px rgba(0,0,0,.25); display:flex; flex-direction:column; overflow:hidden; }
.head { display:flex; align-items:flex-start; justify-content:space-between; padding:18px 24px 14px; border-bottom:1px solid var(--border,#e5e7eb); }
.titles h2 { margin:0; font-size:18px; font-weight:800; color:var(--text1,#111827); }
.titles p  { margin:4px 0 0; font-size:13px; color:var(--text3,#9ca3af); }
.close-btn { background:transparent; border:none; width:32px; height:32px; border-radius:8px; cursor:pointer; display:inline-flex; align-items:center; justify-content:center; transition:background .15s; }
.close-btn:hover { background:var(--bg,#f5f7f6); }

.body { flex:1; display:grid; grid-template-columns:1.8fr 1fr; gap:16px; padding:16px 20px 20px; min-height:0; }
.chart, .table { background:var(--bg,#f8faf9); border-radius:12px; padding:14px 16px; min-height:0; display:flex; flex-direction:column; }
.table { overflow:auto; }
.state { display:flex; align-items:center; justify-content:center; flex:1; color:var(--text3,#9ca3af); font-size:14px; }
.state.err { color:#dc2626; }

.fade-enter-active, .fade-leave-active { transition:opacity .2s; }
.fade-enter-from, .fade-leave-to { opacity:0; }

@media (max-width: 1000px) {
  .body { grid-template-columns:1fr; grid-template-rows:1fr 1fr; }
}
</style>
