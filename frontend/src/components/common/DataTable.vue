<template>
  <div>
    <div style="overflow-x: auto">
      <table class="dt">
        <thead>
          <tr>
            <th v-for="col in columns" :key="col.key" :style="{ textAlign: col.align || 'left' }">
              <component v-if="col.headerRender" :is="{ render: () => col.headerRender!() }" />
              <span v-else>{{ col.title }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="paged.length === 0">
            <td :colspan="columns.length" class="empty">{{ emptyText }}</td>
          </tr>
          <tr v-for="(row, i) in paged" :key="i" class="dt-row">
            <td v-for="col in columns" :key="col.key" :style="{ textAlign: col.align || 'left', whiteSpace: col.wrap ? 'normal' : 'nowrap' }">
              <component v-if="col.render" :is="{ render: () => col.render!(row[col.key], row, offset + i) }" />
              <span v-else>{{ row[col.key] ?? '—' }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-if="pagination" class="pg">
      <span class="pg-info">共 {{ data.length }} 条</span>
      <button class="pg-btn" :disabled="page <= 1" @click="page--"><AppIcon name="chevronLeft" :size="14" /></button>
      <template v-for="(p, i) in visiblePages" :key="i">
        <button v-if="typeof p === 'number'" class="pg-btn" :class="{ active: page === p }" @click="page = p">{{ p }}</button>
        <span v-else class="pg-dots">…</span>
      </template>
      <button class="pg-btn" :disabled="page >= totalPages" @click="page++"><AppIcon name="chevronRight" :size="14" /></button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import AppIcon from './AppIcon.vue'
import type { TableColumn } from '@/types'

const props = withDefaults(defineProps<{
  columns: TableColumn[]
  data: Record<string, unknown>[]
  pagination?: boolean
  pageSize?: number
  emptyText?: string
}>(), { pagination: false, pageSize: 20, emptyText: '暂无数据' })

const page       = ref(1)
const totalPages = computed(() => Math.max(1, Math.ceil(props.data.length / props.pageSize)))
const offset     = computed(() => (page.value - 1) * props.pageSize)
const paged      = computed(() =>
  props.pagination ? props.data.slice(offset.value, offset.value + props.pageSize) : props.data
)

// 可见页号 —— 总是显示 5 个页码,过长时中间用 '…' 占位
//   total ≤ 6        → 全显示
//   当前页 ≤ 3       → [1,2,3,4,5,…,N]
//   当前页 ≥ N-2     → [1,…,N-4,N-3,N-2,N-1,N]
//   其余(中段)      → [1,…,cur-1,cur,cur+1,…,N]
const visiblePages = computed<(number | '...')[]>(() => {
  const total = totalPages.value
  const cur = page.value
  if (total <= 6) return Array.from({ length: total }, (_, i) => i + 1)
  if (cur <= 3) return [1, 2, 3, 4, 5, '...', total]
  if (cur >= total - 2) return [1, '...', total - 4, total - 3, total - 2, total - 1, total]
  return [1, '...', cur - 1, cur, cur + 1, '...', total]
})
</script>

<style scoped>
.dt { width: 100%; border-collapse: collapse; font-size: 13px; }
.dt thead th { padding: 11px 14px; font-weight: 700; font-size: 12px; color: var(--text3); border-bottom: 2px solid var(--border); white-space: nowrap; text-transform: uppercase; letter-spacing: .04em; }
.dt tbody td { padding: 12px 14px; color: var(--text1); border-bottom: 1px solid var(--border); }
.dt-row:hover { background: var(--green-50); }
.empty { padding: 40px; text-align: center; color: var(--text3); }
.pg { display: flex; align-items: center; justify-content: flex-end; gap: 6px; padding: 12px 0 0; }
.pg-info { font-size: 13px; color: var(--text2); margin-right: 4px; }
.pg-btn { width: 32px; height: 32px; border-radius: 8px; background: var(--card); border: 1px solid var(--border); color: var(--text1); display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 13px; font-weight: 500; transition: all .15s; }
.pg-btn:disabled { background: #f1f5f0; color: var(--text3); cursor: not-allowed; }
.pg-btn.active   { background: var(--green); border-color: var(--green); color: #fff; font-weight: 700; }
.pg-dots         { display: inline-flex; align-items: center; justify-content: center; width: 24px; height: 32px; color: var(--text3); font-size: 14px; user-select: none; }
</style>
