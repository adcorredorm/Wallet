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
} from 'chart.js'
import type { DashboardWidget } from '@/types/dashboard'
import { useWidgetData } from '@/composables/useWidgetData'
import BaseSpinner from '@/components/ui/BaseSpinner.vue'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

const CHART_COLORS = [
  '#6366f1', '#f59e0b', '#10b981', '#ef4444', '#3b82f6',
  '#8b5cf6', '#f97316', '#14b8a6', '#ec4899', '#84cc16',
]

const COLOR_GRID = 'rgba(51, 65, 85, 0.5)'
const COLOR_TICK = '#94a3b8'
const COLOR_TOOLTIP_BG = '#1e293b'
const COLOR_TOOLTIP_TEXT = '#f1f5f9'

const props = defineProps<{
  widget: DashboardWidget
  displayCurrency: string
}>()

const { result, loading, isEmpty } = useWidgetData(
  computed(() => props.widget),
  computed(() => props.displayCurrency),
)

const chartData = computed(() => ({
  labels: result.value?.labels ?? [],
  datasets: (result.value?.datasets ?? []).map((ds, i) => ({
    label: ds.label,
    data: ds.data,
    backgroundColor: CHART_COLORS[i % CHART_COLORS.length] + 'cc',
    borderColor: CHART_COLORS[i % CHART_COLORS.length],
    borderWidth: 1,
    borderRadius: 3,
  })),
}))

const chartOptions: ChartOptions<'bar'> = {
  responsive: true,
  maintainAspectRatio: false,
  animation: { duration: 200 },
  plugins: {
    legend: {
      display: true,
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
}
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
