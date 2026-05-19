<template>
  <div class="card">
    <div v-if="title || $slots.extra" class="card-header">
      <div>
        <div class="card-title">{{ title }}</div>
        <div v-if="subtitle" class="card-subtitle">{{ subtitle }}</div>
      </div>
      <slot name="extra" />
    </div>
    <div class="card-body" :style="{ padding }"><slot /></div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ title?: string; subtitle?: string; padding?: string }>(), {
  title: '', subtitle: '', padding: '20px 22px',
})
</script>

<style scoped>
.card { background: var(--card); border-radius: var(--r); box-shadow: var(--shadow); overflow: hidden;
display: flex; flex-direction: column;  }
.card-header {
  padding: 18px 22px 14px; display: flex; justify-content: space-between;
  align-items: center; border-bottom: 1px solid var(--border);
}
.card-title   { font-weight: 700; font-size: 15px; color: var(--text1); }
.card-subtitle{ font-size: 12px; color: var(--text3); margin-top: 2px; }
.card-body    { flex: 1; display: flex; flex-direction: column; min-height: 0; }
/* 当 body 内只有一个子元素(典型:仅一个 EChartBox)时,垂直居中 */
.card-body > :only-child { margin: auto 0; }
</style>
