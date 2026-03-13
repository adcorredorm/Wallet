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

// day_of_week uses a different result format: labels = day names, 1 dataset with 7 values.
// Standard format: each dataset = one group (category/account/type), labels = time buckets.
const isDayOfWeek = computed(() => props.widget.config.group_by === 'day_of_week')

const arcStyles = { borderColor: '#1e293b', borderWidth: 2, hoverOffset: 4 }

const chartData = computed(() => {
  if (!result.value) return { labels: [], datasets: [{ data: [], backgroundColor: [], ...arcStyles }] }

  if (isDayOfWeek.value) {
    // day_of_week: result.labels = 7 day names, result.datasets[0].data = 7 values
    return {
      labels: result.value.labels,
      datasets: [{
        data: result.value.datasets[0]?.data ?? [],
        backgroundColor: CHART_COLORS.slice(0, result.value.labels.length),
        ...arcStyles,
      }],
    }
  }

  // Standard: each dataset is one slice; sum its time-bucket data for the arc value
  return {
    labels: result.value.datasets.map((ds) => ds.label),
    datasets: [{
      data: result.value.datasets.map((ds) => ds.data.reduce((acc, val) => acc + val, 0)),
      backgroundColor: CHART_COLORS.slice(0, result.value.datasets.length),
      ...arcStyles,
    }],
  }
})

const chartOptions = computed<ChartOptions<'doughnut'>>(() => ({
  responsive: true,
  maintainAspectRatio: false,
  animation: { duration: 200 },
  plugins: {
    legend: {
      display: true,
      position: 'right' as const,
      labels: {
        color: COLOR_TICK,
        boxWidth: 12,
        padding: 8,
        font: { size: 11 },
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
