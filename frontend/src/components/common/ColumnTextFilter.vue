<template>
  <div ref="wrapEl" class="cf-wrap">
    <button type="button" class="cf-trigger" :class="{ active: hasFilter, open }" @click="toggleOpen">
      <span class="cf-title">{{ title }}</span>
      <span class="cf-icon">▾</span>
      <span v-if="hasFilter" class="cf-dot" :title="`已筛选:${modelValue}`"></span>
    </button>
    <div v-if="open" class="cf-popup">
      <input
        ref="inputEl"
        v-model="draft"
        type="text"
        class="cf-input"
        :placeholder="`输入${title}...`"
        @keydown.enter="confirm"
        @keydown.esc="cancel"
      />
      <div class="cf-actions">
        <button type="button" class="cf-bar-btn cf-bar-btn--cancel" @click="cancel">取消</button>
        <button type="button" class="cf-bar-btn cf-bar-btn--ok" @click="confirm">确定</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, watch, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps<{
  title: string
  /** 当前过滤关键字。空字符串 = 不过滤 */
  modelValue: string
}>()
const emit = defineEmits<{ (e: 'update:modelValue', value: string): void }>()

const open = ref(false)
const draft = ref(props.modelValue)
const wrapEl = ref<HTMLElement | null>(null)
const inputEl = ref<HTMLInputElement | null>(null)

const hasFilter = computed(() => props.modelValue.trim().length > 0)

// 父组件外部清空时同步草稿
watch(() => props.modelValue, v => { draft.value = v })

async function toggleOpen(): Promise<void> {
  open.value = !open.value
  if (open.value) {
    draft.value = props.modelValue
    await nextTick()
    inputEl.value?.focus()
    inputEl.value?.select()
  }
}

function confirm(): void {
  emit('update:modelValue', draft.value.trim())
  open.value = false
}

function cancel(): void {
  draft.value = props.modelValue
  open.value = false
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
.cf-trigger:hover .cf-title  { color: var(--green-dark); }
.cf-trigger.active .cf-title { color: var(--green-dark); }
.cf-trigger.open  .cf-icon   { transform: rotate(180deg); }
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
  min-width: 220px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.cf-input {
  padding: 8px 10px;
  border: 1.5px solid var(--border);
  border-radius: 7px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text1);
  outline: none;
  background: #fff;
  font-family: inherit;
  text-transform: none;
  letter-spacing: 0;
  transition: border-color .12s;
}
.cf-input:focus { border-color: var(--green); }
.cf-actions { display: flex; gap: 6px; }
.cf-bar-btn { flex: 1; padding: 6px 10px; border: none; font-size: 12px; font-weight: 700; border-radius: 6px; cursor: pointer; transition: background .12s; text-transform: none; letter-spacing: 0; }
.cf-bar-btn--cancel { background: #f1f5f0; color: var(--text2); }
.cf-bar-btn--cancel:hover { background: #e5e7eb; }
.cf-bar-btn--ok { background: var(--green); color: #fff; }
.cf-bar-btn--ok:hover { background: var(--green-dark); }
</style>
