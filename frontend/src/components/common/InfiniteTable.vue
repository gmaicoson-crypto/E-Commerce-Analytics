<template>
  <div class="inf-table">
    <!-- 顶部哨兵:在视口里 → 卡头还可见 → 隐藏回到顶部按钮 -->
    <div ref="topSentinelEl" class="inf-top-sentinel" aria-hidden="true"></div>

    <DataTable :columns="columns" :data="rows" :pagination="false" :empty-text="loading && rows.length === 0 ? '加载中…' : '暂无数据'" />

    <!-- 底部哨兵 + 状态提示 -->
    <div ref="sentinelEl" class="inf-sentinel">
      <span v-if="loading">加载中…</span>
      <span v-else-if="!hasMore && rows.length > 0">— 已加载全部 {{ total }} 条 —</span>
      <span v-else-if="!hasMore && rows.length === 0">&nbsp;</span>
    </div>

    <!-- 悬浮回到顶部按钮 -->
    <Transition name="back-fade">
      <button v-show="showBackToTop" class="back-to-top" type="button" title="回到顶部" @click="scrollToTop">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <line x1="12" y1="19" x2="12" y2="5"></line>
          <polyline points="5 12 12 5 19 12"></polyline>
        </svg>
      </button>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import DataTable from './DataTable.vue'
import type { TableColumn } from '@/types'

interface LoaderResult {
  data: Record<string, unknown>[]
  total: number
}

const props = withDefaults(
  defineProps<{
    columns: TableColumn[]
    /** 加载第 page 页(每页 pageSize 条),返回 {data, total} */
    loader: (page: number, pageSize: number) => Promise<LoaderResult>
    /** 每页大小,默认 50 */
    pageSize?: number
    /** 该 key 变化时,清空已加载数据并从第 1 页重新拉取(用于日期/状态等筛选切换) */
    resetKey?: unknown
    /** 可选 CSS 选择器:当该元素整体滚出视口顶部时显示「回到顶部」按钮。
     *  常见用法:传 KPI 卡所在容器的 class(如 ".kpi-grid")。
     *  不传则观察内置 1px 顶部哨兵(行为同表格本身)。 */
    triggerSelector?: string
  }>(),
  { pageSize: 50 },
)

const rows = ref<Record<string, unknown>[]>([])
const page = ref(0)              // 已加载到的页码;0 表示尚未开始
const total = ref(0)
const loading = ref(false)
const sentinelEl = ref<HTMLElement | null>(null)
const topSentinelEl = ref<HTMLElement | null>(null)
const showBackToTop = ref(false)
let observer: IntersectionObserver | null = null
let topObserver: IntersectionObserver | null = null
let scrollContainer: HTMLElement | Window = window
let loadId = 0   // 防止 resetKey 切换时旧请求乱序

/** MainLayout 的真实滚动容器是 .content(flex:1; overflow:auto),而非 window。
 *  找不到就退回 window。 */
function findScrollContainer(): HTMLElement | Window {
  return (document.querySelector('.content') as HTMLElement | null) ?? window
}

const hasMore = computed(() => rows.value.length < total.value || page.value === 0)

async function loadNext(): Promise<void> {
  if (loading.value) return
  if (page.value > 0 && rows.value.length >= total.value) return
  loading.value = true
  const myId = ++loadId
  const nextPage = page.value + 1
  try {
    const r = await props.loader(nextPage, props.pageSize)
    if (myId !== loadId) return  // 期间发生了 reset,丢弃结果
    rows.value.push(...r.data)
    total.value = r.total
    page.value = nextPage
    // 加载完后若 sentinel 仍在视口(列表太短),继续拉下一页
    await nextTick()
    if (sentinelEl.value && hasMore.value && isInViewport(sentinelEl.value)) {
      loading.value = false
      loadNext()
      return
    }
  } catch (e) {
    console.error('[InfiniteTable] loader failed', e)
  } finally {
    if (myId === loadId) loading.value = false
  }
}

function isInViewport(el: HTMLElement): boolean {
  const r = el.getBoundingClientRect()
  // 用真实滚动容器的可视区高度;若容器不是 Element 退回 window 高度
  let viewTop = 0
  let viewBottom = window.innerHeight || document.documentElement.clientHeight
  if (!(scrollContainer instanceof Window)) {
    const cr = scrollContainer.getBoundingClientRect()
    viewTop = cr.top
    viewBottom = cr.bottom
  }
  return r.top < viewBottom && r.bottom > viewTop
}

function reset(): void {
  loadId++  // 让正在进行的请求失效
  rows.value = []
  page.value = 0
  total.value = 0
  loading.value = false
  loadNext()
}

function scrollToTop(): void {
  // 用真实滚动容器(.content)而非 window;在 MainLayout 下 window 不滚动
  if (scrollContainer instanceof Window) {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  } else {
    scrollContainer.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

// resetKey 变化时重新加载
watch(() => props.resetKey, () => reset())

onMounted(() => {
  scrollContainer = findScrollContainer()
  // IntersectionObserver 的 root 必须是 Element(或 null=viewport),不能传 Window
  const obsRoot: Element | null = scrollContainer instanceof Window ? null : scrollContainer

  // 底部哨兵:进入视口时拉下一页(提前 300px 触发,体验顺滑)
  observer = new IntersectionObserver(
    (entries) => {
      const entry = entries[0]
      if (entry?.isIntersecting && hasMore.value && !loading.value) loadNext()
    },
    { root: obsRoot, rootMargin: '300px 0px' },
  )
  if (sentinelEl.value) observer.observe(sentinelEl.value)

  // 顶部触发元素:优先使用外部传入的 triggerSelector(如 KPI 卡所在容器),
  // 不传则用 InfiniteTable 自己上方的 1px 哨兵
  const externalTrigger = props.triggerSelector
    ? (document.querySelector(props.triggerSelector) as HTMLElement | null)
    : null
  const triggerEl = externalTrigger ?? topSentinelEl.value

  if (triggerEl) {
    topObserver = new IntersectionObserver(
      (entries) => {
        const entry = entries[0]
        if (!entry) return
        // 触发元素整体滚出视口顶部 → 显示「回到顶部」
        showBackToTop.value = !entry.isIntersecting
      },
      { root: obsRoot, threshold: 0 },
    )
    topObserver.observe(triggerEl)
  }

  // 初次加载
  loadNext()
})

onBeforeUnmount(() => {
  observer?.disconnect()
  topObserver?.disconnect()
})

defineExpose({ reset, total })
</script>

<style scoped>
.inf-table { position: relative; }

/* 1px 顶部哨兵 — 不占视觉空间,只给 IntersectionObserver 用 */
.inf-top-sentinel { height: 1px; }

.inf-sentinel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 18px 0;
  font-size: 12px;
  color: var(--text3);
  min-height: 40px;
}

.back-to-top {
  position: fixed;
  right: 28px;
  bottom: 36px;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: none;
  background: var(--green);
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 6px 18px rgba(45, 106, 79, 0.32);
  z-index: 60;
  transition: background .15s, transform .15s, box-shadow .15s;
}
.back-to-top:hover {
  background: var(--green-dark);
  transform: translateY(-2px);
  box-shadow: 0 8px 22px rgba(45, 106, 79, 0.4);
}

.back-fade-enter-active, .back-fade-leave-active { transition: opacity .2s, transform .2s; }
.back-fade-enter-from, .back-fade-leave-to       { opacity: 0; transform: translateY(8px); }
</style>
