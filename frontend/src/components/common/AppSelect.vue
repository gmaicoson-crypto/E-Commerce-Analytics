<template>
  <select class="app-select" :value="modelValue" @change="emit('update:modelValue', ($event.target as HTMLSelectElement).value)">
    <option v-for="o in options" :key="o.value" :value="o.value">{{ o.label }}</option>
  </select>
</template>

<script setup lang="ts">
defineProps<{ modelValue: string; options: { value: string; label: string }[] }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
</script>

<style scoped>
.app-select {
  padding: 6px 12px; border-radius: 8px; border: 1.5px solid var(--border);
  font-size: 13px; font-weight: 600; color: var(--text1);
  background: white; cursor: pointer; outline: none; font-family: inherit;
}
</style>
