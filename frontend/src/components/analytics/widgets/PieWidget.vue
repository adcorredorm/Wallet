<script setup lang="ts">
/**
 * PieWidget — Doughnut chart for proportional breakdown widgets.
 *
 * Why Doughnut instead of Pie?
 * At small mobile sizes (the primary viewport), a doughnut's hollow center
 * preserves more visual clarity. The center space can also display a summary
 * value in future iterations without overlapping the arc labels.
 *
 * Data shape transformation:
 * useWidgetData returns a time-series shape (labels = time buckets, datasets =
 * groups). A pie chart needs the inverse: each dataset (group) becomes one arc,
 * and its value is the sum of all its data points. This way a "spending by
 * category for last 30 days" widget correctly shows one slice per category
 * regardless of which time granularity the config uses.
 *
 * Why ArcElement registration?
 * Doughnut/Pie charts render arcs rather than points, lines, or bars. Registering
 * only ArcElement keeps the Chart.js bundle footprint minimal.
 */

import { computed } from 'vue'
import { Doughnut } from 'vue-chartjs'
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
  type ChartOptions,
  type TooltipItem,
} from 'chart.js'
import type { DashboardWidget } from '@/types/dashboard'
import { useWidgetData } from '@/composables/useWidgetData'
import BaseSpinner from '@/components/ui/BaseSpinner.vue'
import { CHART_COLORS, COLOR_TICK, COLOR_TOOLTIP_BG, COLOR_TOOLTIP_TEXT } from '@/utils/chartColors'

ChartJS.register(ArcElement, Tooltip, Legend)

const props = defineProps<{
  widget: DashboardWidget
  displayCurrency: string
}>()

const { result, loading, isEmpty } = useWidgetData(
  computed(() => props.widget),
  computed(() => props.displayCurrency),
)

// Each dataset (group) becomes one arc. Its value is the sum of all time buckets
// in that dataset — collapsing the time dimension into a single proportional value.
const chartData = computed(() => ({
  labels: result.value?.datasets.map((ds) => ds.label) ?? [],
  datasets: [
    {
      data: result.value?.datasets.map((ds) =>
        ds.data.reduce((acc, val) => acc + val, 0),
      ) ?? [],
      backgroundColor: CHART_COLORS.slice(0, result.value?.datasets.length ?? 0),
      borderColor: '#1e293b',  // dark-bg-secondary — creates a subtle gap between arcs
      borderWidth: 2,
      hoverOffset: 4,
    },
  ],
}))

const chartOptions = computed<ChartOptions<'doughnut'>>(() => ({
  responsive: true,
  maintainAspectRatio: false,
  animation: { duration: 200 },
  plugins: {
    legend: {
      display: true,
      position: 'bottom' as const,
      labels: {
        color: COLOR_TICK,
        boxWidth: 12,
        padding: 12,
        // Limit legend text length to prevent overflow on narrow mobile screens
        generateLabels: (chart) => {
          const original = ChartJS.defaults.plugins.legend.labels.generateLabels(chart)
          return original.map((item) => ({
            ...item,
            text: item.text.length > 20 ? item.text.slice(0, 18) + '…' : item.text,
          }))
        },
      },
    },
    tooltip: {
      backgroundColor: COLOR_TOOLTIP_BG,
      titleColor: COLOR_TICK,
      bodyColor: COLOR_TOOLTIP_TEXT,
      borderColor: 'rgba(51, 65, 85, 0.8)',
      borderWidth: 1,
      callbacks: {
        label: (context: TooltipItem<'doughnut'>) => {
          const value = (context.raw as number) ?? 0
          return new Intl.NumberFormat('es-CO', {
            style: 'currency',
            currency: props.displayCurrency,
            maximumFractionDigits: 0,
          }).format(value)
        },
      },
    },
  },
}))
</script>

<template>
  <div class="flex flex-col h-full p-3 bg-dark-bg-secondary rounded-lg">
    <h3 class="text-sm font-medium text-dark-text-secondary mb-2 truncate">
      {{ props.widget.title }}
    </h3>
    <div class="flex-1 flex items-center justify-center min-h-0">
      <BaseSpinner v-if="loading" />
      <p
        v-else-if="isEmpty"
        class="text-sm text-dark-text-tertiary"
      >
        Sin datos
      </p>
      <div
        v-else
        class="w-full h-full"
        style="position: relative"
      >
        <Doughnut :data="chartData" :options="chartOptions" />
      </div>
    </div>
  </div>
</template>
