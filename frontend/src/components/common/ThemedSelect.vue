<template>
  <div
    ref="wrapEl"
    class="ts-wrap"
  >
    <button
      type="button"
      class="ts-trigger"
      :class="{ open }"
      @click="toggle"
    >
      <span class="ts-text">{{ displayLabel }}</span>
    </button>
    <div
      v-if="open"
      class="ts-popup"
      role="listbox"
    >
      <div
        v-for="opt in options"
        :key="opt.value"
        class="ts-opt"
        :class="{ active: modelValue === opt.value }"
        role="option"
        @click="pick(opt.value)"
      >
        {{ opt.label }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/* 主题风格下拉选择组件 */
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'

export interface ThemedSelectOption {
  label: string
  value: string
}

const props = withDefaults(
  defineProps<{
    modelValue: string
    options: ReadonlyArray<ThemedSelectOption>   
    placeholder?: string
    minWidth?: number | string
  }>(),
  { placeholder: '请选择', minWidth: 144 },
)

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'change', value: string): void
}>()

const open = ref(false)
const wrapEl = ref<HTMLElement | null>(null)

const displayLabel = computed(
  () => props.options.find((o) => o.value === props.modelValue)?.label ?? props.placeholder,
)
const triggerMinWidth = computed(
  () => typeof props.minWidth === 'number' ? `${props.minWidth}px` : props.minWidth,
)

function toggle(): void {
  open.value = !open.value
}
function pick(value: string): void {
  open.value = false
  if (value === props.modelValue) return
  emit('update:modelValue', value)
  emit('change', value)
}
function onDocMouseDown(e: MouseEvent): void {
  if (!open.value) return
  const target = e.target as Node | null
  if (target && wrapEl.value && !wrapEl.value.contains(target)) {
    open.value = false
  }
}

onMounted(() => document.addEventListener('mousedown', onDocMouseDown))
onBeforeUnmount(() => document.removeEventListener('mousedown', onDocMouseDown))
</script>

<style scoped>
.ts-wrap {
  position: relative;
}

.ts-trigger {
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 7px 12px;
  border: 1.5px solid var(--border, #e5e7eb);
  border-radius: 8px;
  background: var(--card, #fff);
  font-size: 13px;
  font-weight: 400;
  color: var(--text1, #111827);
  cursor: pointer;
  min-width: v-bind(triggerMinWidth);
  transition: border-color 0.15s, background-color 0.15s, box-shadow 0.15s;
}

.ts-trigger::after {
  content: '';
  width: 12px;
  height: 12px;
  background: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%232d6a4f' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'><polyline points='6 9 12 15 18 9'/></svg>") center/contain no-repeat;
  flex-shrink: 0;
  transition: transform 0.15s;
}

.ts-trigger:hover {
  border-color: var(--green, #52b788);
  background-color: var(--green-50, #f0fdf4);
}

.ts-trigger.open {
  border-color: var(--green, #52b788);
  box-shadow: 0 0 0 3px rgba(82, 183, 136, 0.18);
}

.ts-trigger.open::after {
  transform: rotate(180deg);
}

.ts-text {
  flex: 1;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ts-popup {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  min-width: 100%;
  background: var(--card, #fff);
  border: 1.5px solid var(--border, #e5e7eb);
  border-radius: 10px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.12);
  padding: 4px;
  z-index: 10001;
  max-height: 280px;
  overflow-y: auto;
}

.ts-opt {
  padding: 7px 12px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text1, #111827);
  cursor: pointer;
  white-space: nowrap;
  transition: background-color 0.12s, color 0.12s;
}

.ts-opt:hover {
  background: var(--green-50, #f0fdf4);
  color: var(--green-dark, #2d6a4f);
}

.ts-opt.active {
  background: var(--green, #52b788);
  color: #fff;
}

.ts-opt.active:hover {
  background: var(--green-dark, #2d6a4f);
  color: #fff;
}
</style>
