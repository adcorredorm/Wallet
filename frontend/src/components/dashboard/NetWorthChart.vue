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
 * Range presets (stock-app style):
 * Seven presets (1D / 1S / 1M / 1A / YTD / 5A / Todo) each compute a
 * rangeDays value that is fed into useNetWorthHistory. The composable's own
 * selectGranularity() function then auto-selects the appropriate granularity
 * (day / week / month / year) based on that range — no override is passed from
 * this component. Default preset on mount: 1M (30 days).
 *
 * "Todo" preset:
 * Requires an async IndexedDB query on mount to discover the oldest
 * transaction or transfer date. Until that query resolves, the "Todo" button
 * uses a temporary fallback of 1825 days (≈5 years) so the chart is never
 * blank if the user clicks it before the query finishes.
 */

import { ref, computed, onMounted } from 'vue'
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
import {
  differenceInDays,
  startOfYear,
  parseISO,
} from 'date-fns'
import { useNetWorthHistory } from '@/composables/useNetWorthHistory'
import { useSettingsStore } from '@/stores/settings'
import { formatCurrency } from '@/utils/formatters'
import { db } from '@/offline'

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

// ── Range presets ──────────────────────────────────────────────────────────
// Each preset is identified by its label (used as the selection key).
// rangeDays is the number of calendar days to show ending at today; the
// composable computes startDate = subDays(today, rangeDays - 1) internally.
//
// Dynamic presets (YTD, Todo) store null as a placeholder and are resolved
// at mount time. A reactive ref (rangeDaysForPreset) holds the resolved value
// for each dynamic preset so the chart can react if the user switches to them
// after the async resolution completes.
interface RangePreset {
  label: string
  // Static number of days, or null if the value is resolved async / dynamically.
  staticDays: number | null
}

const PRESETS: RangePreset[] = [
  { label: '1D',   staticDays: 1    },
  { label: '1S',   staticDays: 7    },
  { label: '1M',   staticDays: 30   },   // default
  { label: '1A',   staticDays: 365  },
  { label: 'YTD',  staticDays: null },   // resolved at mount: Jan 1 → today
  { label: '5A',   staticDays: 1825 },
  { label: 'Todo', staticDays: null },   // resolved at mount: oldest record → today
]

// Resolved day counts for the two dynamic presets.
// Fallbacks keep the chart functional even if the user clicks before mount resolves.
const ytdDays = ref<number>(computeYtdDays())
const todoDays = ref<number>(1825) // fallback ≈5 years until DB query resolves

function computeYtdDays(): number {
  const today = new Date()
  const jan1 = startOfYear(today)
  // +1 so the range is inclusive: Jan 1 itself is the opening data point
  return differenceInDays(today, jan1) + 1
}

// Resolve the "Todo" range by finding the oldest date across all transactions
// and transfers in IndexedDB. Both tables are indexed on 'date' so orderBy()
// is efficient (uses the index, no full table scan).
async function resolveOldestDate(): Promise<void> {
  const [oldestTx, oldestTr] = await Promise.all([
    db.transactions.orderBy('date').first(),
    db.transfers.orderBy('date').first(),
  ])

  const dates: string[] = []
  if (oldestTx?.date) dates.push(oldestTx.date)
  if (oldestTr?.date) dates.push(oldestTr.date)

  if (dates.length === 0) return // no records yet — keep fallback

  const oldestDateStr = dates.sort()[0]  // lexicographic sort is correct for YYYY-MM-DD
  const oldestDate = parseISO(oldestDateStr)
  const today = new Date()
  // +1 for an inclusive range that includes the oldest date itself as a boundary
  todoDays.value = differenceInDays(today, oldestDate) + 1
}

onMounted(() => {
  // YTD is a pure calculation — no async needed, but we refresh it on mount
  // in case the component is kept alive across a date boundary (e.g. midnight).
  ytdDays.value = computeYtdDays()
  // "Todo" requires an IndexedDB query to find the oldest financial event.
  void resolveOldestDate()
})

// ── Preset selection ───────────────────────────────────────────────────────
const selectedLabel = ref<string>('1M') // default preset

// Derive the effective rangeDays from the selected preset.
// Static presets resolve immediately; dynamic ones use their reactive refs.
const rangeDays = computed<number>(() => {
  const preset = PRESETS.find(p => p.label === selectedLabel.value)
  if (!preset) return 30
  if (preset.staticDays !== null) return preset.staticDays
  if (preset.label === 'YTD') return ytdDays.value
  if (preset.label === 'Todo') return todoDays.value
  return 30
})

function selectPreset(preset: RangePreset): void {
  selectedLabel.value = preset.label
}

// ── Composable ─────────────────────────────────────────────────────────────
const settingsStore = useSettingsStore()

// We pass only rangeDays with no granularity override.
// useNetWorthHistory's selectGranularity() auto-selects:
//   ≤90 days   → day   (covers 1D, 1S, 1M)
//   ≤365 days  → week  (covers 1A; YTD when <1 year)
//   ≤1095 days → month (covers 5A; YTD if multi-year edge; Todo for medium history)
//   >1095 days → year  (covers Todo for long histories)
const { dataPoints, loading, isEmpty } = useNetWorthHistory({
  rangeDays,
})

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
    <!-- Header row: title + range preset selector -->
    <div class="flex items-center justify-between gap-2">
      <h2 class="text-sm font-medium text-dark-text-secondary shrink-0">
        Evolución del Patrimonio
      </h2>

      <!-- Range preset pill group — stock-app style (1D / 1S / 1M / 1A / YTD / 5A / Todo) -->
      <!-- The outer div uses overflow-x-auto so on very narrow screens the pills
           can scroll horizontally rather than wrapping, which would push the chart
           down and consume vertical space. -->
      <div
        class="flex bg-dark-bg-tertiary rounded-lg p-0.5 overflow-x-auto"
        role="group"
        aria-label="Seleccionar rango del gráfico"
      >
        <button
          v-for="preset in PRESETS"
          :key="preset.label"
          class="px-2.5 py-1.5 text-xs font-medium rounded-md transition-colors duration-150 whitespace-nowrap min-h-[32px]"
          :class="
            selectedLabel === preset.label
              ? 'bg-blue-500 text-white'
              : 'text-dark-text-secondary hover:text-dark-text-primary'
          "
          :aria-pressed="selectedLabel === preset.label"
          @click="selectPreset(preset)"
        >
          {{ preset.label }}
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
