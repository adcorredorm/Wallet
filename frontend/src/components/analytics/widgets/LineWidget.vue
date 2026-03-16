<script setup lang="ts">
/**
 * LineWidget — Time-series line chart for dashboard widgets.
 *
 * Why explicit ChartJS.register() instead of importing auto-registered components?
 * Tree-shaking: we only bundle the Chart.js modules this widget actually uses.
 * Importing all of Chart.js would add ~200KB to the bundle. On mobile, bundle
 * size directly impacts First Contentful Paint on slower connections.
 *
 * Why computed() wrappers around props for useWidgetData?
 * The composable's watchEffect() tracks reactive dependencies. Passing
 * computed(() => props.widget) gives watchEffect a proper Ref to track, so
 * the chart automatically re-renders when the parent passes a different widget
 * or the dashboard's displayCurrency changes.
 *
 * Why maintainAspectRatio: false?
 * The parent container (dashboard grid cell) controls height via CSS. Without
 * this flag, Chart.js ignores our container height and enforces its own 2:1
 * aspect ratio, which breaks fixed-height grid layouts on mobile.
 *
 * Why hex colors instead of Tailwind classes for Chart.js?
 * Chart.js reads colors from JavaScript options at render time — it cannot
 * read CSS classes or CSS custom properties. We use the same dark-mode palette
 * defined in tailwind.config.js as hex literals.
 */

import { computed } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  type ChartOptions,
  type TooltipItem,
} from 'chart.js'
import type { DashboardWidget } from '@/types/dashboard'
import { useWidgetData } from '@/composables/useWidgetData'
import BaseSpinner from '@/components/ui/BaseSpinner.vue'
import { CHART_COLORS, COLOR_GRID, COLOR_TICK, COLOR_TOOLTIP_BG, COLOR_TOOLTIP_TEXT } from '@/utils/chartColors'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler)

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
    borderColor: CHART_COLORS[i % CHART_COLORS.length],
    backgroundColor: CHART_COLORS[i % CHART_COLORS.length] + '20',
    tension: 0.3,
    fill: false,
    borderWidth: 2,
    pointRadius: ds.data.length <= 1 ? 4 : 0,  // show point when only one data point (no line to draw)
    pointHoverRadius: 4,
  })),
}))

const chartOptions = computed<ChartOptions<'line'>>(() => ({
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
      callbacks: {
        label: (context: TooltipItem<'line'>) => {
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
      ticks: { color: COLOR_TICK, maxTicksLimit: 6, maxRotation: 0 },
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
      <!-- position: relative required by Chart.js when maintainAspectRatio is false -->
      <div
        v-else
        class="w-full h-full"
        style="position: relative"
      >
        <Line :data="chartData" :options="chartOptions" />
      </div>
    </div>
  </div>
</template>
