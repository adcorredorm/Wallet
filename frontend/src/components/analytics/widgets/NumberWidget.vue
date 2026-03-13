<script setup lang="ts">
/**
 * NumberWidget — Large formatted currency number for KPI-style widgets.
 *
 * No Chart.js needed here — this widget renders a single aggregated value, making
 * it perfect for KPIs like "total income this month" or "total expenses this year".
 *
 * Why sum Object.values(totals)?
 * useWidgetData returns a totals record keyed by group (e.g. { income: 500, expense: 300 }).
 * For a number widget, the intent is typically a grand total across all groups.
 * Summing all totals gives the correct aggregate regardless of how group_by is
 * configured. If the widget config uses group_by: 'none', totals will have a
 * single 'Total' key, so the sum equals that single value anyway.
 *
 * Why Intl.NumberFormat with 'es-CO' locale?
 * The app targets a Colombian Spanish-speaking user. 'es-CO' formats numbers
 * using periods as thousands separators and commas as decimal separators
 * (e.g. $1.500.000), which matches local financial conventions.
 * maximumFractionDigits: 0 rounds to whole currency units for large amounts —
 * fractional cents add noise to KPI values at dashboard scale.
 */

import { computed } from 'vue'
import type { DashboardWidget } from '@/types/dashboard'
import { useWidgetData } from '@/composables/useWidgetData'
import BaseSpinner from '@/components/ui/BaseSpinner.vue'

const props = defineProps<{
  widget: DashboardWidget
  displayCurrency: string
}>()

const { result, loading, isEmpty } = useWidgetData(
  computed(() => props.widget),
  computed(() => props.displayCurrency),
)

// Grand total: sum all group totals into a single displayable number.
// Object.values returns [] for null/undefined-safe access after the null guard.
const total = computed<number>(() => {
  if (!result.value) return 0
  return Object.values(result.value.totals).reduce((acc, val) => acc + val, 0)
})

const formatted = computed<string>(() =>
  new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: props.displayCurrency,
    maximumFractionDigits: 0,
  }).format(total.value),
)
</script>

<template>
  <div class="flex flex-col h-full p-3 bg-dark-bg-secondary rounded-lg">
    <h3 class="text-sm font-medium text-dark-text-secondary mb-2 truncate">
      {{ props.widget.title }}
    </h3>
    <div class="flex-1 flex items-center justify-center">
      <BaseSpinner v-if="loading" />
      <p
        v-else-if="isEmpty"
        class="text-sm text-dark-text-tertiary"
      >
        Sin datos
      </p>
      <!-- text-3xl on mobile, text-4xl on wider screens for better use of space -->
      <span
        v-else
        class="text-3xl font-bold text-dark-text-primary text-center leading-tight
               md:text-4xl"
      >
        {{ formatted }}
      </span>
    </div>
  </div>
</template>
