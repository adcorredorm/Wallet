<script setup lang="ts">
/**
 * NetWorthChart — Net worth evolution line chart.
 *
 * Why vue-chartjs instead of a custom canvas implementation?
 * vue-chartjs manages the Chart.js instance lifecycle with Vue — it calls
 * chart.destroy() when the component unmounts, preventing memory leaks from
 * orphaned canvas contexts (a common mobile performance issue).
 *
 * Why Chart.js explicit hex colors instead of CSS variables?
 * Chart.js reads options at render time via JavaScript, not via CSS. We pass
 * our dark-mode palette colors as hex values so the chart always matches the
 * app's dark theme without a runtime CSS variable lookup.
 *
 * Segmented control:
 * Four granularity options (Día/Sem/Mes/Año) each map to a preset range and
 * override the auto-selected granularity of useNetWorthHistory. Selecting a
 * segment also sets the corresponding range so the chart always shows a
 * sensible window.
 */

import { ref, computed } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Filler,
  type ChartOptions,
  type TooltipItem,
} from 'chart.js'
import { useNetWorthHistory, type Granularity } from '@/composables/useNetWorthHistory'
import { useSettingsStore } from '@/stores/settings'
import { formatCurrency } from '@/utils/formatters'

// Register only the Chart.js components we use — tree-shaking the rest.
// CategoryScale: maps our date strings to x-axis positions
// LinearScale: maps net worth values to y-axis positions
// PointElement + LineElement: renders the line and individual data points
// Filler: enables the area fill below the line
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Filler
)

// ── Color constants — our dark-mode palette ────────────────────────────────
const COLOR_LINE = '#3b82f6'               // blue-500 (app accent)
const COLOR_FILL_TOP = 'rgba(59, 130, 246, 0.2)'
const COLOR_FILL_BOTTOM = 'rgba(59, 130, 246, 0)'
const COLOR_GRID = 'rgba(51, 65, 85, 0.5)' // slate-700 at 50%
const COLOR_TICK = '#94a3b8'               // slate-400
const COLOR_TOOLTIP_BG = '#1e293b'         // dark-bg-secondary
const COLOR_TOOLTIP_TEXT = '#f1f5f9'       // dark-text-primary

// ── Granularity control ────────────────────────────────────────────────────
interface GranularityOption {
  label: string
  value: Granularity
  rangeDays: number
}

const GRANULARITY_OPTIONS: GranularityOption[] = [
  { label: 'Día', value: 'day', rangeDays: 30 },
  { label: 'Sem', value: 'week', rangeDays: 90 },
  { label: 'Mes', value: 'month', rangeDays: 365 },
  { label: 'Año', value: 'year', rangeDays: 1825 },
]

const selectedOption = ref<GranularityOption>(GRANULARITY_OPTIONS[0])
const rangeDays = ref(30)

const settingsStore = useSettingsStore()

const { dataPoints, loading, isEmpty } = useNetWorthHistory({
  rangeDays,
  granularity: computed(() => selectedOption.value.value),
})

function selectGranularity(option: GranularityOption) {
  selectedOption.value = option
  rangeDays.value = option.rangeDays
}

// ── Chart data ─────────────────────────────────────────────────────────────
const chartData = computed(() => {
  const points = dataPoints.value
  return {
    labels: points.map(p => p.date),
    datasets: [
      {
        data: points.map(p => p.value),
        borderColor: COLOR_LINE,
        // Build fill gradient via factory function — Chart.js calls this with
        // the chart context so we can create a CanvasGradient at render time.
        // Using a static color string as fallback before chartArea is available.
        backgroundColor: (context: { chart: { ctx: CanvasRenderingContext2D; chartArea?: { top: number; bottom: number } } }) => {
          const { ctx, chartArea } = context.chart
          if (!chartArea) return COLOR_FILL_TOP
          const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom)
          gradient.addColorStop(0, COLOR_FILL_TOP)
          gradient.addColorStop(1, COLOR_FILL_BOTTOM)
          return gradient
        },
        fill: true,
        borderWidth: 2,
        // Hide individual point dots on dense data (>60 points) for readability
        pointRadius: points.length > 60 ? 0 : 3,
        pointHoverRadius: 5,
        tension: 0.3, // slight curve for a smoother line
      }
    ]
  }
})

// ── Chart options ──────────────────────────────────────────────────────────
const chartOptions = computed<ChartOptions<'line'>>(() => ({
  responsive: true,
  // maintainAspectRatio: false is required when the container has a fixed height.
  // Without it, Chart.js will override our 220px height to maintain its own ratio.
  maintainAspectRatio: false,
  interaction: {
    mode: 'index' as const,
    intersect: false, // tooltip shows on hover anywhere on the vertical axis
  },
  plugins: {
    legend: { display: false }, // no legend — the chart title is self-explanatory
    tooltip: {
      backgroundColor: COLOR_TOOLTIP_BG,
      titleColor: COLOR_TICK,
      bodyColor: COLOR_TOOLTIP_TEXT,
      borderColor: 'rgba(51, 65, 85, 0.8)',
      borderWidth: 1,
      padding: 12,
      callbacks: {
        label: (context: TooltipItem<'line'>) => {
          return formatCurrency(context.parsed.y ?? 0, settingsStore.primaryCurrency)
        },
      },
    },
  },
  scales: {
    x: {
      grid: { color: COLOR_GRID },
      ticks: {
        color: COLOR_TICK,
        maxTicksLimit: 6,
        // Never rotate x-axis labels — horizontal labels are more readable on mobile
        maxRotation: 0,
      },
    },
    y: {
      grid: { color: COLOR_GRID },
      ticks: {
        color: COLOR_TICK,
        callback: (value: number | string) =>
          formatCurrency(Number(value), settingsStore.primaryCurrency, true),
      },
    },
  },
  animation: { duration: 200 },
}))
</script>

<template>
  <div class="card p-4 space-y-3">
    <!-- Header row: title + segmented granularity control -->
    <div class="flex items-center justify-between">
      <h2 class="text-sm font-medium text-dark-text-secondary">
        Evolución del Patrimonio
      </h2>

      <!-- Segmented control -->
      <!-- min-h-[32px] on each button ensures touch targets remain accessible
           while the outer group uses p-0.5 for a compact pill appearance -->
      <div
        class="flex bg-dark-bg-tertiary rounded-lg p-0.5"
        role="group"
        aria-label="Seleccionar granularidad del gráfico"
      >
        <button
          v-for="option in GRANULARITY_OPTIONS"
          :key="option.value"
          class="px-3 py-1.5 text-xs font-medium rounded-md transition-colors duration-150 min-w-[44px] min-h-[32px]"
          :class="
            selectedOption.value === option.value
              ? 'bg-blue-500 text-white'
              : 'text-dark-text-secondary hover:text-dark-text-primary'
          "
          :aria-pressed="selectedOption.value === option.value"
          @click="selectGranularity(option)"
        >
          {{ option.label }}
        </button>
      </div>
    </div>

    <!-- Skeleton loader — shown while async computation is in progress -->
    <div
      v-if="loading"
      class="animate-pulse bg-dark-bg-tertiary rounded-lg"
      style="height: 220px"
      aria-label="Cargando gráfico de patrimonio"
      role="status"
    />

    <!-- Empty state — shown when no financial events exist in IndexedDB -->
    <div
      v-else-if="isEmpty"
      class="flex flex-col items-center justify-center rounded-lg border border-dark-bg-tertiary text-center px-6"
      style="height: 220px"
    >
      <p class="text-sm text-dark-text-secondary leading-relaxed">
        Registra tu primera transacción para ver la evolución de tu patrimonio
      </p>
    </div>

    <!-- Chart canvas — 220px fixed height, relative positioning required by
         Chart.js when maintainAspectRatio is false -->
    <div
      v-else
      style="height: 220px; position: relative"
    >
      <Line
        :data="chartData"
        :options="chartOptions"
      />
    </div>
  </div>
</template>
