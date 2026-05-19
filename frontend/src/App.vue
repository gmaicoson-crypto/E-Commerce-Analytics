<template>
  <RouterView />
  <ChartDetailModal />
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'
import { useAuthStore } from '@/stores/authStore'
import ChartDetailModal from '@/components/common/ChartDetailModal.vue'

const auth = useAuthStore()

onMounted(() => {
  auth.restoreToken()
})
</script>
