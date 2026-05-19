<template>
  <div class="ph">
    <div>
      <h1 class="ph-title">{{ title }}</h1>
      <p v-if="subtitle" class="ph-sub">{{ subtitle }}</p>
    </div>
    <div v-if="$slots.actions" class="ph-actions"><slot name="actions" /></div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ title: string; subtitle?: string }>()
</script>

<style scoped>
.ph        { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 22px; }
.ph-title  { font-size: 24px; font-weight: 900; color: var(--text1); line-height: 1.2; }
.ph-sub    { font-size: 13px; color: var(--text2); margin-top: 4px; }
.ph-actions{ display: flex; gap: 10px; align-items: center; }
</style>
