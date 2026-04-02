<!-- frontend/src/components/budgets/BudgetProgressBar.vue -->
<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  percentage: number  // 0–100+
  height?: string     // default 'h-2'
}>()

const barWidth = computed(() => `${Math.min(props.percentage, 100)}%`)

const colorClass = computed(() => {
  if (props.percentage >= 90) return 'bg-red-500'
  if (props.percentage >= 70) return 'bg-yellow-500'
  return 'bg-green-500'
})
</script>

<template>
  <div :class="['w-full bg-dark-bg-tertiary rounded-full overflow-hidden', height ?? 'h-2']">
    <div
      :class="['h-full rounded-full transition-all duration-300', colorClass]"
      :style="{ width: barWidth }"
    />
  </div>
</template>
