<script setup lang="ts">
/**
 * BarWidget — Grouped vertical bar chart for dashboard widgets.
 *
 * Uses `Bar` from vue-chartjs instead of Line because bar charts communicate
 * discrete comparisons (e.g. spending per category this month) more clearly
 * than a line, which implies continuity between data points.
 *
 * BarElement registration: unlike Line charts, Bar requires BarElement instead
 * of PointElement + LineElement. We only register what we use to keep the
 * bundle lean.
 */

import { computed } from 'vue'
import { Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  type ChartOptions,
  type TooltipItem,
} from 'chart.js'
import type { DashboardWidget } from '@/types/dashboard'
import { useWidgetData } from '@/composables/useWidgetData'
import BaseSpinner from '@/components/ui/BaseSpinner.vue'
import { CHART_COLORS, COLOR_GRID, COLOR_TICK, COLOR_TOOLTIP_BG, COLOR_TOOLTIP_TEXT } from '@/utils/chartColors'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

const props = defineProps<{
  widget: DashboardWidget
  displayCurrency: string
}>()

const { result, loading, isEmpty } = useWidgetData(
  computed(() => props.widget),
  computed(() => props.displayCurrency),
)

// day_of_week uses 1 dataset with 7 bars — give each bar its own color
const isDayOfWeek = computed(() => props.widget.config.group_by === 'day_of_week')

const chartData = computed(() => ({
  labels: result.value?.labels ?? [],
  datasets: (result.value?.datasets ?? []).map((ds, i) => ({
    label: ds.label,
    data: ds.data,
    // day_of_week: array of colors (one per bar); time-series: single color per dataset
    backgroundColor: isDayOfWeek.value
      ? ds.data.map((_, j) => CHART_COLORS[j % CHART_COLORS.length] + 'cc')
      : CHART_COLORS[i % CHART_COLORS.length] + 'cc',
    borderColor: isDayOfWeek.value
      ? ds.data.map((_, j) => CHART_COLORS[j % CHART_COLORS.length])
      : CHART_COLORS[i % CHART_COLORS.length],
    borderWidth: 1,
    borderRadius: 3,
  })),
}))

const chartOptions = computed<ChartOptions<'bar'>>(() => ({
  responsive: true,
  maintainAspectRatio: false,
  animation: { duration: 200 },
  plugins: {
    legend: {
      // Hide legend for day_of_week: x-axis labels already identify each bar
      display: !isDayOfWeek.value,
      labels: { color: COLOR_TICK, boxWidth: 12, padding: 12 },
    },
    tooltip: {
      mode: 'index' as const,
      intersect: false,
      backgroundColor: COLOR_TOOLTIP_BG,
      titleColor: COLOR_TICK,
      bodyColor: COLOR_TOOLTIP_TEXT,
      borderColor: 'rgba(51, 65, 85, 0.8)',
      borderWidth: 1,
      callbacks: {
        label: (context: TooltipItem<'bar'>) => {
          const value = context.parsed.y ?? 0
          return new Intl.NumberFormat('es-CO', {
            style: 'currency',
            currency: props.displayCurrency,
            maximumFractionDigits: 0,
          }).format(value)
        },
      },
    },
  },
  scales: {
    x: {
      grid: { color: COLOR_GRID },
      ticks: { color: COLOR_TICK, maxTicksLimit: 8, maxRotation: 0 },
    },
    y: {
      beginAtZero: true,
      grid: { color: COLOR_GRID },
      ticks: { color: COLOR_TICK },
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
        <Bar :data="chartData" :options="chartOptions" />
      </div>
    </div>
  </div>
</template>
