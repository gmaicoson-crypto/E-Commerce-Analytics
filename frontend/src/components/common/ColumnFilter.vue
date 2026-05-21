<template>
  <div ref="wrapEl" class="cf-wrap">
    <button type="button" class="cf-trigger" :class="{ active: hasFilter, open }" @click="open = !open">
      <span class="cf-title">{{ title }}</span>
      <span class="cf-icon">▾</span>
      <span v-if="hasFilter" class="cf-dot" :title="`已筛选 ${selected.length} 项`"></span>
    </button>
    <div v-if="open" class="cf-popup" role="listbox">
      <div class="cf-toolbar">
        <button type="button" class="cf-bar-btn" @click="selectAll">全选</button>
        <button type="button" class="cf-bar-btn" @click="clear">清空</button>
      </div>
      <div class="cf-options">
        <label v-for="o in options" :key="o.value" class="cf-opt">
          <input type="checkbox" :checked="selectedSet.has(o.value)" @change="toggle(o.value)" />
          <span>{{ o.label }}</span>
        </label>
        <div v-if="options.length === 0" class="cf-empty">暂无可选项</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'

export interface ColumnFilterOption {
  label: string
  value: string
}

const props = defineProps<{
  title: string
  options: ReadonlyArray<ColumnFilterOption>
  /** 已选中的 value 列表。空数组 = 不过滤(全部显示) */
  selected: string[]
}>()
const emit = defineEmits<{ (e: 'update:selected', value: string[]): void }>()

const open = ref(false)
const wrapEl = ref<HTMLElement | null>(null)

const selectedSet = computed(() => new Set(props.selected))
const hasFilter = computed(() => props.selected.length > 0 && props.selected.length < props.options.length)

function emitUpdate(next: string[]): void {
  emit('update:selected', next)
}
function toggle(value: string): void {
  const s = new Set(props.selected)
  if (s.has(value)) s.delete(value)
  else s.add(value)
  emitUpdate(Array.from(s))
}
function selectAll(): void {
  emitUpdate(props.options.map(o => o.value))
}
function clear(): void {
  emitUpdate([])
}
function onDocMouseDown(e: MouseEvent): void {
  if (!open.value) return
  const t = e.target as Node | null
  if (t && wrapEl.value && !wrapEl.value.contains(t)) open.value = false
}

onMounted(() => document.addEventListener('mousedown', onDocMouseDown))
onBeforeUnmount(() => document.removeEventListener('mousedown', onDocMouseDown))
</script>

<style scoped>
.cf-wrap { position: relative; display: inline-block; }
.cf-trigger {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 0;
  border: none;
  background: transparent;
  cursor: pointer;
  font: inherit;
  color: inherit;
  text-transform: inherit;
  letter-spacing: inherit;
  font-weight: 700;
  font-size: 12px;
}
.cf-trigger:hover .cf-title { color: var(--green-dark); }
.cf-trigger.active .cf-title { color: var(--green-dark); }
.cf-trigger.open  .cf-icon  { transform: rotate(180deg); }
.cf-title { font-weight: 700; }
.cf-icon  { font-size: 10px; color: var(--text3); transition: transform .15s; }
.cf-dot   { width: 6px; height: 6px; border-radius: 99px; background: var(--green); }

.cf-popup {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  z-index: 10001;
  background: #fff;
  border: 1.5px solid var(--border);
  border-radius: 10px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, .12);
  min-width: 180px;
  max-width: 240px;
  display: flex;
  flex-direction: column;
}
.cf-toolbar { display: flex; gap: 6px; padding: 8px 8px 4px; border-bottom: 1px dashed var(--border); }
.cf-bar-btn { flex: 1; padding: 5px 8px; border: none; background: var(--green-50); color: var(--green-dark); font-size: 12px; font-weight: 700; border-radius: 6px; cursor: pointer; transition: background .12s; }
.cf-bar-btn:hover { background: var(--green-100); }
.cf-options { padding: 6px; max-height: 260px; overflow-y: auto; display: flex; flex-direction: column; gap: 2px; }
.cf-opt {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text1);
  cursor: pointer;
  text-transform: none;
  letter-spacing: 0;
}
.cf-opt:hover { background: var(--green-50); }
.cf-opt input { width: 14px; height: 14px; cursor: pointer; accent-color: var(--green); flex-shrink: 0; }
.cf-empty { padding: 16px; text-align: center; font-size: 12px; color: var(--text3); }
</style>
