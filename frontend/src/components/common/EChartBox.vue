<template>
  <div ref="elRef" class="echart-box" :style="{ '--h': height + 'px' }" />
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'

const props = withDefaults(defineProps<{ option: EChartsOption; height?: number }>(), { height: 240 })

const elRef = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null
let ro: ResizeObserver | null = null

function init() {
  if (!elRef.value) return
  chart = echarts.init(elRef.value)
  chart.setOption(props.option)
}

function resize() { chart?.resize() }

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

watch(() => props.option, (opt) => chart?.setOption(opt, true), { deep: true })
</script>

<style scoped>
.echart-box {
  width: 100%;
  height: var(--h);  /* 默认按传入像素高度;与兄弟元素并存时尊重此值 */
}
/* 当 EChartBox 是父容器唯一子元素时,撑满父高度,
   ECharts 内部按更大画布重新计算 grid 留白,纵坐标标签不会被挤压 */
.echart-box:only-child {
  height: 100%;
  min-height: var(--h);
}
</style>
