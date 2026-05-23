<template>
  <div class="pg">
    <span class="pg-info">共 {{ total }} 条</span>
    <button
      class="pg-btn"
      :disabled="page <= 1"
      @click="goto(page - 1)"
    >
      <AppIcon
        name="chevronLeft"
        :size="14"
      />
    </button>
    <template
      v-for="(p, i) in visiblePages"
      :key="i"
    >
      <button
        v-if="typeof p === 'number'"
        class="pg-btn"
        :class="{ active: page === p }"
        @click="goto(p)"
      >{{ p }}</button>
      <span
        v-else
        class="pg-dots"
      >…</span>
    </template>
    <button
      class="pg-btn"
      :disabled="page >= totalPages"
      @click="goto(page + 1)"
    >
      <AppIcon
        name="chevronRight"
        :size="14"
      />
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from './AppIcon.vue'

const props = defineProps<{
  page: number
  total: number
  pageSize: number
}>()
const emit = defineEmits<{
  (e: 'update:page', value: number): void
}>()

const totalPages = computed(
  () => Math.max(1, Math.ceil(props.total / props.pageSize)),
)

// 可见页号 —— 总是显示 5 个页码,过长时中间用 '…' 占位(与 DataTable 同款)
const visiblePages = computed<(number | '...')[]>(() => {
  const total = totalPages.value
  const cur = props.page
  if (total <= 6) return Array.from({ length: total }, (_, i) => i + 1)
  if (cur <= 3) return [1, 2, 3, 4, 5, '...', total]
  if (cur >= total - 2) return [1, '...', total - 4, total - 3, total - 2, total - 1, total]
  return [1, '...', cur - 1, cur, cur + 1, '...', total]
})

function goto(p: number): void {
  if (p < 1 || p > totalPages.value || p === props.page) return
  emit('update:page', p)
}
</script>

<style scoped>
.pg {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  padding: 12px 0 0;
}

.pg-info {
  font-size: 13px;
  color: var(--text2);
  margin-right: 4px;
}

.pg-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--card);
  border: 1px solid var(--border);
  color: var(--text1);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.15s;
}

.pg-btn:disabled {
  background: #f1f5f0;
  color: var(--text3);
  cursor: not-allowed;
}

.pg-btn.active {
  background: var(--green);
  border-color: var(--green);
  color: #fff;
  font-weight: 700;
}

.pg-dots {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 32px;
  color: var(--text3);
  font-size: 14px;
  user-select: none;
}
</style>
