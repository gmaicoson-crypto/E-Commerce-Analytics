<template>
  <div
    ref="elRef"
    class="echart-box"
    :style="{ '--h': `${height}px` }"
  />
</template>

<script setup lang="ts">
import * as echarts from 'echarts'
import type { ECBasicOption } from 'echarts/types/dist/shared'
import { onMounted, onUnmounted, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    option: unknown
    height?: number
  }>(),
  {
    height: 240,
  },
)

const elRef = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null
let ro: ResizeObserver | null = null

function init() {
  if (!elRef.value) {
    return
  }

  chart = echarts.init(elRef.value)
  chart.setOption(props.option as ECBasicOption)
}

function resize() {
  chart?.resize()
}

onMounted(() => {
  init()
  window.addEventListener('resize', resize)
  if (elRef.value && typeof ResizeObserver !== 'undefined') {
    ro = new ResizeObserver(resize)
    ro.observe(elRef.value)
  }
})

onUnmounted(() => {
  chart?.dispose()
  chart = null
  window.removeEventListener('resize', resize)
  ro?.disconnect()
  ro = null
})

watch(
  () => props.option,
  (opt) => chart?.setOption(opt as ECBasicOption, true),
  { deep: true },
)
</script>

<style scoped>
.echart-box {
  width: 100%;
  height: var(--h);
}

.echart-box:only-child {
  height: 100%;
  min-height: var(--h);
}
</style>
