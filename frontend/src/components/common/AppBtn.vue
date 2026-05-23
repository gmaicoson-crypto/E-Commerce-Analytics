<template>
  <button
    class="app-btn"
    :class="[`btn-${variant}`, `btn-${size}`]"
    :disabled="disabled"
    @click="emit('click')"
  >
    <AppIcon v-if="icon" :name="icon" :size="14" />
    <slot />
  </button>
</template>

<script setup lang="ts">
import AppIcon from './AppIcon.vue'

withDefaults(
  defineProps<{
    variant?: string
    size?: string
    icon?: string
    disabled?: boolean
  }>(),
  {
    variant: 'primary',
    size: 'md',
    icon: '',
    disabled: false,
  },
)

const emit = defineEmits<{ click: [] }>()
</script>

<style scoped>
.app-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: none;
  border-radius: var(--r-sm);
  cursor: pointer;
  font-family: inherit;
  font-weight: 700;
  transition: all 0.15s;
}

.app-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-md {
  padding: 9px 18px;
  font-size: 13px;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 12px;
}

.btn-primary {
  background: var(--green);
  color: #fff;
}

.btn-outline {
  border: 1.5px solid var(--green);
  background: transparent;
  color: var(--green);
}

.btn-ghost {
  background: var(--green-50);
  color: var(--green-dark);
}

.btn-danger {
  background: #fee2e2;
  color: #dc2626;
}
</style>
