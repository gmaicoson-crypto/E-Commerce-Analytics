<template>
  <div class="kpi-card">
    <div class="kpi-top">
      <span class="kpi-title">{{ title }}</span>
      <div
        v-if="icon"
        class="kpi-icon"
        :style="{ background: iconBg || 'var(--green-100)' }"
      >
        <AppIcon :name="icon" :size="18" color="var(--green-dark)" />
      </div>
    </div>
    <div
      class="kpi-value"
      :class="{ ticking: ticking }"
    >{{ prefix }}{{ display }}{{ suffix }}</div>
    <div v-if="change !== undefined" class="kpi-footer">
      <span class="kpi-badge" :style="isPos ? posBadge : negBadge">
        <AppIcon
          :name="isPos ? 'trendUp' : 'trendDown'"
          :size="11"
          :color="isPos ? '#16a34a' : '#dc2626'"
        />
        {{ Math.abs(change) }}%
      </span>
      <span class="kpi-label">{{ changeLabel ?? '同比' }}</span>
    </div>
    <div v-else-if="subValue !== undefined && subValue !== ''" class="kpi-footer">
      <span class="kpi-subval">{{ subValue }}</span>
      <span class="kpi-label">{{ subLabel ?? '金额' }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
/* 指标卡片组件 */
import { computed, ref, watch, onBeforeUnmount, onMounted } from 'vue'
import AppIcon from './AppIcon.vue'

const props = withDefaults(
  defineProps<{
    title: string
    value: string | number
    change?: number
    changeLabel?: string
    subValue?: string
    subLabel?: string
    icon?: string
    iconBg?: string
    prefix?: string
    suffix?: string
  }>(),
  { prefix: '', suffix: '' },
)

const isPos = computed(() => (props.change ?? 0) >= 0)
const posBadge = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: '3px',
  fontSize: '12px',
  fontWeight: 700,
  padding: '2px 8px',
  borderRadius: '99px',
  background: '#dcfce7',
  color: '#16a34a',
}
const negBadge = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: '3px',
  fontSize: '12px',
  fontWeight: 700,
  padding: '2px 8px',
  borderRadius: '99px',
  background: '#fee2e2',
  color: '#dc2626',
}

interface Parsed {
  num: number
  decimals: number
  thousands: boolean
  suffix: string
}

function parseLeadingNumber(s: string): Parsed | null {
  const m = String(s).match(/^([+-]?[0-9][\d,]*(?:\.\d+)?)(.*)$/)
  if (!m) return null
  const numStr = m[1]
  const rest = m[2] ?? ''
  const n = Number(numStr.replace(/,/g, ''))
  if (!Number.isFinite(n)) return null
  const decimals = numStr.includes('.') ? (numStr.split('.')[1]?.length ?? 0) : 0
  return { num: n, decimals, thousands: numStr.includes(','), suffix: rest }
}

function format(n: number, p: Parsed): string {
  const head = p.thousands
    ? n.toLocaleString(undefined, { minimumFractionDigits: p.decimals, maximumFractionDigits: p.decimals })
    : n.toFixed(p.decimals)
  return head + p.suffix
}

const display = ref<string | number>(props.value)
const ticking = ref(false)
let raf: number | null = null

function cancel(): void {
  if (raf !== null) {
    cancelAnimationFrame(raf)
    raf = null
  }
}

function runTween(from: number, to: number, fmt: Parsed): void {
  cancel()
  if (from === to) {
    display.value = format(to, fmt)
    ticking.value = false
    return
  }
  const start = performance.now()
  const dur = 600
  ticking.value = true
  const tick = (now: number) => {
    const t = Math.min(1, (now - start) / dur)
    const eased = 1 - Math.pow(1 - t, 3) 
    const v = from + (to - from) * eased
    display.value = format(v, fmt)
    if (t < 1) {
      raf = requestAnimationFrame(tick)
    } else {
      raf = null
      ticking.value = false
    }
  }
  raf = requestAnimationFrame(tick)
}

watch(
  () => props.value,
  (next, prev) => {
  const cur = parseLeadingNumber(String(prev ?? ''))
  const dst = parseLeadingNumber(String(next ?? ''))
  if (!dst) {
    cancel()
    display.value = next
    ticking.value = false
    return
  }
  
  const from = cur ? cur.num : 0
  if (from === dst.num) {
    cancel()
    display.value = next
    ticking.value = false
    return
  }
  
  if (cur && cur.suffix !== dst.suffix && cur.num !== 0) {
    cancel()
    display.value = next
    ticking.value = false
    return
  }
  runTween(from, dst.num, dst)
  },
)

onMounted(() => {
  const dst = parseLeadingNumber(String(props.value ?? ''))
  if (dst && dst.num !== 0) {
    display.value = format(0, dst)
    runTween(0, dst.num, dst)
  }
})

onBeforeUnmount(cancel)
</script>

<style scoped>
.kpi-card {
  background: var(--card);
  border-radius: var(--r);
  padding: 20px 22px;
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 1;
}

.kpi-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.kpi-title {
  font-size: 13px;
  color: var(--text2);
  font-weight: 600;
}

.kpi-icon {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.kpi-value {
  font-size: 26px;
  font-weight: 800;
  color: var(--text1);
  line-height: 1;
  font-variant-numeric: tabular-nums;
  transition: color 0.15s;
}

.kpi-value.ticking {
  color: var(--green-dark);
}

.kpi-footer {
  display: flex;
  align-items: center;
  gap: 6px;
}

.kpi-label {
  font-size: 12px;
  color: var(--text3);
}

.kpi-subval {
  font-size: 13px;
  font-weight: 800;
  color: var(--text2);
  font-variant-numeric: tabular-nums;
}
</style>
