<script setup lang="ts">
/**
 * Currency Display Component
 *
 * Why a component for currency?
 * - Consistent formatting across app
 * - Color coding for positive/negative
 * - Optional compact format for mobile
 * - Size variants for different contexts
 */

import { computed } from 'vue'
import { formatCurrency } from '@/utils/formatters'

interface Props {
  amount: number
  currency?: string
  size?: 'sm' | 'md' | 'lg' | 'xl'
  compact?: boolean
  showSign?: boolean // Show + for positive numbers
  colorize?: boolean // Color code positive (green) / negative (red)
}

const props = withDefaults(defineProps<Props>(), {
  currency: 'USD',
  size: 'md',
  compact: false,
  showSign: false,
  colorize: false
})

const formattedAmount = computed(() => {
  const n = Number(props.amount)
  let formatted = formatCurrency(Math.abs(n), props.currency, props.compact)

  if (props.showSign && n > 0) {
    formatted = '+' + formatted
  } else if (n < 0) {
    formatted = '-' + formatted
  }

  return formatted
})

const colorClass = computed(() => {
  if (!props.colorize) return ''
  return Number(props.amount) >= 0 ? 'text-accent-green' : 'text-accent-red'
})

const sizeClasses = {
  sm: 'text-sm',
  md: 'text-base',
  lg: 'text-lg',
  xl: 'text-2xl font-bold'
}
</script>

<template>
  <span
    :class="[
      'font-medium tabular-nums',
      sizeClasses[size],
      colorClass
    ]"
  >
    {{ formattedAmount }}
  </span>
</template>
