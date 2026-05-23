<template>
  <div class="tab-bar">
    <button v-for="t in tabs" :key="t.id" class="tab-item" :class="{ active: active === t.id }" @click="emit('change', t.id)">
      {{ t.label }}
    </button>
  </div>
</template>

<script setup lang="ts">
defineProps<{ 
  tabs: { id: string; label: string }[]
  active: string 
}>()
const emit = defineEmits<{change: [id: string] }>()
</script>

<style scoped>
.tab-bar { 
  display: flex; 
  gap: 4px; 
  background: var(--green-50); 
  border-radius: 10px; 
  padding: 4px; 
}
.tab-item { 
  padding: 7px 18px; 
  border-radius: 7px; 
  font-size: 13px; 
  font-weight: 700;
  background: transparent; 
  color: var(--text2); 
  transition: all .15s; 
  cursor: pointer; 
}
.tab-item.active { 
  background: #fff; 
  color: var(--green-dark); 
  box-shadow: var(--shadow); 
}
</style>
