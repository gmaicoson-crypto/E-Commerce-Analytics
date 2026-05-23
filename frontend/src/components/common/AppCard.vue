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
/* 通用卡片容器组件 */
withDefaults(
  defineProps<{
    title?: string
    subtitle?: string
    padding?: string
  }>(),
  {
    title: '',
    subtitle: '',
    padding: '20px 22px',
  },
)
</script>

<style scoped>
.card {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: var(--r);
  background: var(--card);
  box-shadow: var(--shadow);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 22px 14px;
  border-bottom: 1px solid var(--border);
}

.card-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text1);
}

.card-subtitle {
  margin-top: 2px;
  font-size: 12px;
  color: var(--text3);
}

.card-body {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
}

.card-body > :only-child {
  margin: auto 0;
}
</style>
