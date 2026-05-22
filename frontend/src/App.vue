<template>
  <RouterView />
  <ChartDetailModal />
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
import ChartDetailModal from '@/components/common/ChartDetailModal.vue'
</script>
