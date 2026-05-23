<template>
  <span :style="style">{{ label }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { BadgeColor } from '@/types'
import { BADGE_MAP } from '@/utils/constants'

const props = withDefaults(
  defineProps<{
    label: string
    color?: BadgeColor
    size?: 'sm' | 'md'
  }>(),
  {
    color: 'green',
    size: 'sm',
  },
)

const style = computed(() => {
  const color = BADGE_MAP[props.color] ?? BADGE_MAP.gray

  return {
    display: 'inline-flex',
    alignItems: 'center',
    padding: props.size === 'sm' ? '2px 9px' : '4px 12px',
    borderRadius: '99px',
    fontSize: props.size === 'sm' ? '12px' : '13px',
    fontWeight: 700,
    background: color.bg,
    color: color.fg,
  }
})
</script>
