<template>
  <div class="inf-table">
    <div
      ref="topSentinelEl"
      class="inf-top-sentinel"
      aria-hidden="true"
    ></div>

    <DataTable
      :columns="columns"
      :data="rows"
      :pagination="false"
      :empty-text="loading && rows.length === 0 ? '加载中…' : '暂无数据'"
    />

    <div
      ref="sentinelEl"
      class="inf-sentinel"
    >
      <span v-if="loading">加载中…</span>
      <span v-else-if="!hasMore && rows.length > 0">— 已加载全部 {{ total }} 条 —</span>
      <span v-else-if="!hasMore && rows.length === 0">&nbsp;</span>
    </div>

    <Transition name="back-fade">
      <button
        v-show="showBackToTop"
        class="back-to-top"
        type="button"
        title="回到顶部"
        @click="scrollToTop"
      >
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <line x1="12" y1="19" x2="12" y2="5"></line>
          <polyline points="5 12 12 5 19 12"></polyline>
        </svg>
      </button>
    </Transition>
  </div>
</template>

<script setup lang="ts">
/* 支持滚动加载的表格组件 */
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
    loader: (page: number, pageSize: number) => Promise<LoaderResult>
    pageSize?: number
    resetKey?: unknown
    triggerSelector?: string
  }>(),
  { pageSize: 50 },
)

const rows = ref<Record<string, unknown>[]>([])
const page = ref(0)
const total = ref(0)
const loading = ref(false)
const sentinelEl = ref<HTMLElement | null>(null)
const topSentinelEl = ref<HTMLElement | null>(null)
const showBackToTop = ref(false)
let observer: IntersectionObserver | null = null
let topObserver: IntersectionObserver | null = null
let scrollContainer: HTMLElement | Window = window
let loadId = 0 

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
    if (myId !== loadId) return 
    rows.value.push(...r.data)
    total.value = r.total
    page.value = nextPage
    
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
  loadId++ 
  rows.value = []
  page.value = 0
  total.value = 0
  loading.value = false
  loadNext()
}

function scrollToTop(): void {
  
  if (scrollContainer instanceof Window) {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  } else {
    scrollContainer.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

watch(
  () => props.resetKey,
  () => reset(),
)

onMounted(() => {
  scrollContainer = findScrollContainer()
  
  const obsRoot: Element | null = scrollContainer instanceof Window ? null : scrollContainer

  observer = new IntersectionObserver(
    (entries) => {
      const entry = entries[0]
      if (entry?.isIntersecting && hasMore.value && !loading.value) loadNext()
    },
    { root: obsRoot, rootMargin: '300px 0px' },
  )
  if (sentinelEl.value) observer.observe(sentinelEl.value)

  const externalTrigger = props.triggerSelector
    ? (document.querySelector(props.triggerSelector) as HTMLElement | null)
    : null
  const triggerEl = externalTrigger ?? topSentinelEl.value

  if (triggerEl) {
    topObserver = new IntersectionObserver(
      (entries) => {
        const entry = entries[0]
        if (!entry) return
        showBackToTop.value = !entry.isIntersecting
      },
      { root: obsRoot, threshold: 0 },
    )
    topObserver.observe(triggerEl)
  }

  loadNext()
})

onBeforeUnmount(() => {
  observer?.disconnect()
  topObserver?.disconnect()
})

defineExpose({ reset, total })
</script>

<style scoped>
.inf-table {
  position: relative;
}

.inf-top-sentinel {
  height: 1px;
}

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
  transition: background 0.15s, transform 0.15s, box-shadow 0.15s;
}
.back-to-top:hover {
  background: var(--green-dark);
  transform: translateY(-2px);
  box-shadow: 0 8px 22px rgba(45, 106, 79, 0.4);
}

.back-fade-enter-active,
.back-fade-leave-active {
  transition: opacity 0.2s, transform 0.2s;
}

.back-fade-enter-from,
.back-fade-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>
