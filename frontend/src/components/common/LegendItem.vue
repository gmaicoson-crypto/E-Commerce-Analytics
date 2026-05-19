<template>
  <div class="legend-item">
    <span class="dot" :style="{ background: color }" />
    <span class="lbl">{{ label }}</span>
    <span v-if="value" class="val">{{ value }}</span>
    <span v-if="pct !== undefined" class="pct">{{ pct }}%</span>
  </div>
</template>

<script setup lang="ts">
defineProps<{ color: string; label: string; value?: string; pct?: number }>()
</script>

<style scoped>
.legend-item { display: flex; align-items: center; gap: 8px; padding: 5px 0; }
.dot  { width: 10px; height: 10px; border-radius: 3px; flex-shrink: 0; }
.lbl  { flex: 1; font-size: 13px; color: var(--text2); }
.val  { font-size: 13px; font-weight: 700; }
.pct  { font-size: 12px; color: var(--text3); min-width: 38px; text-align: right; }
</style>
