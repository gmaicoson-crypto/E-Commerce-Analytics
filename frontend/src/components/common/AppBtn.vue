<template>
  <button class="app-btn" :class="[`btn-${variant}`, `btn-${size}`]" :disabled="disabled" @click="emit('click')">
    <AppIcon v-if="icon" :name="icon" :size="14" />
    <slot />
  </button>
</template>

<script setup lang="ts">
import AppIcon from './AppIcon.vue'
withDefaults(defineProps<{ variant?: string; size?: string; icon?: string; disabled?: boolean }>(), {
  variant: 'primary', size: 'md', icon: '', disabled: false,
})
const emit = defineEmits<{ click: [] }>()
</script>

<style scoped>
.app-btn {
  display: inline-flex; align-items: center; justify-content: center; gap: 6px;
  border-radius: var(--r-sm); font-weight: 700; cursor: pointer;
  transition: all 0.15s; border: none; font-family: inherit;
}
.app-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-md  { font-size: 13px; padding: 9px 18px; }
.btn-sm  { font-size: 12px; padding: 6px 12px; }
.btn-primary { background: var(--green); color: #fff; }
.btn-outline  { background: transparent; color: var(--green); border: 1.5px solid var(--green); }
.btn-ghost    { background: var(--green-50); color: var(--green-dark); }
.btn-danger   { background: #fee2e2; color: #dc2626; }
</style>
