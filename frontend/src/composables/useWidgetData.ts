/**
 * useWidgetData — Analytics computation engine for dashboard widgets (NF-B2)
 *
 * Reads transactions from IndexedDB (Dexie) and computes reactive analytics
 * results following the same pattern as useNetWorthHistory:
 *   1. Resolve date range from dynamic preset or static bounds
 *   2. Read and filter transactions from IndexedDB
 *   3. Two-step currency conversion (account currency -> primaryCurrency -> displayCurrency)
 *   4. Time bucketing (day/week/month/quarter/semester/year)
 *   5. Grouping (category/account/type/day_of_week/none)
 *   6. Aggregation (sum/avg/count/min/max)
 *   7. Format into AnalyticsResult shape for chart consumption
 *
 * Reactive dependencies: widget config, displayCurrency, primaryCurrency,
 * exchange rates, and transaction store length (triggers recompute on sync).
 */

import { ref, computed, watchEffect, isRef, type Ref } from 'vue'
import {
  format,
  parseISO,
  subDays,
  startOfMonth,
  subMonths,
  endOfMonth,
  startOfQuarter,
  startOfYear,
  subYears,
  startOfISOWeek,
} from 'date-fns'
import { db } from '@/offline'
import type { LocalTransaction, LocalAccount, LocalCategory } from '@/offline'
import { useExchangeRatesStore } from '@/stores/exchangeRates'
import { useSettingsStore } from '@/stores/settings'
import { useTransactionsStore } from '@/stores/transactions'
import { useTransfersStore } from '@/stores/transfers'
import type {
  DashboardWidget,
  AnalyticsResult,
  AnalyticsGranularity,
  Aggregation,
  DynamicTimeRange,
} from '@/types/dashboard'

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const DAY_NAMES = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']

/** Ordered Monday-first for day_of_week output labels */
const DAY_NAMES_ORDERED = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

// ---------------------------------------------------------------------------
// Date range resolution
// ---------------------------------------------------------------------------

function resolvePreset(preset: DynamicTimeRange): { from: string; to: string } {
  const today = new Date()
  const todayStr = format(today, 'yyyy-MM-dd')

  switch (preset) {
    case 'last_7_days':
      return { from: format(subDays(today, 6), 'yyyy-MM-dd'), to: todayStr }
    case 'last_30_days':
      return { from: format(subDays(today, 29), 'yyyy-MM-dd'), to: todayStr }
    case 'last_90_days':
      return { from: format(subDays(today, 89), 'yyyy-MM-dd'), to: todayStr }
    case 'this_month':
      return { from: format(startOfMonth(today), 'yyyy-MM-dd'), to: todayStr }
    case 'last_month': {
      const prevMonth = subMonths(today, 1)
      return {
        from: format(startOfMonth(prevMonth), 'yyyy-MM-dd'),
        to: format(endOfMonth(prevMonth), 'yyyy-MM-dd'),
      }
    }
    case 'this_quarter':
      return { from: format(startOfQuarter(today), 'yyyy-MM-dd'), to: todayStr }
    case 'this_year':
      return { from: format(startOfYear(today), 'yyyy-MM-dd'), to: todayStr }
    case 'last_year': {
      const prevYear = subYears(today, 1)
      return {
        from: format(startOfYear(prevYear), 'yyyy-MM-dd'),
        to: `${prevYear.getFullYear()}-12-31`,
      }
    }
    case 'all_time':
      return { from: '2000-01-01', to: todayStr }
  }
}

// ---------------------------------------------------------------------------
// Time bucketing
// ---------------------------------------------------------------------------

function assignBucket(date: string, granularity: AnalyticsGranularity): string {
  const d = parseISO(date)
  switch (granularity) {
    case 'day':
      return date
    case 'week':
      return format(startOfISOWeek(d), "yyyy-'W'II")
    case 'month':
      return format(d, 'yyyy-MM')
    case 'quarter':
      return `${format(d, 'yyyy')}-Q${Math.ceil((d.getMonth() + 1) / 3)}`
    case 'semester':
      return `${format(d, 'yyyy')}-S${d.getMonth() < 6 ? 1 : 2}`
    case 'year':
      return format(d, 'yyyy')
  }
}

// ---------------------------------------------------------------------------
// Aggregation
// ---------------------------------------------------------------------------

function aggregate(values: number[], aggregation: Aggregation): number {
  if (values.length === 0) return 0
  switch (aggregation) {
    case 'sum':
      return values.reduce((a, b) => a + b, 0)
    case 'avg':
      return values.reduce((a, b) => a + b, 0) / values.length
    case 'count':
      return values.length
    case 'min':
      return values.reduce((a, b) => (b < a ? b : a), values[0])
    case 'max':
      return values.reduce((a, b) => (b > a ? b : a), values[0])
  }
}

// ---------------------------------------------------------------------------
// Composable
// ---------------------------------------------------------------------------

export function useWidgetData(
  widget: Ref<DashboardWidget> | DashboardWidget,
  displayCurrency: Ref<string> | string
): {
  result: Ref<AnalyticsResult | null>
  loading: Ref<boolean>
  isEmpty: Ref<boolean>
} {
  const exchangeRatesStore = useExchangeRatesStore()
  const settingsStore = useSettingsStore()
  const transactionsStore = useTransactionsStore()
  const transfersStore = useTransfersStore()

  // Normalize to computed refs so watchEffect tracks them
  const widgetRef = computed(() => isRef(widget) ? widget.value : widget)
  const displayCurrencyRef = computed(() => isRef(displayCurrency) ? displayCurrency.value : displayCurrency)

  const result = ref<AnalyticsResult | null>(null)
  const loading = ref(false)
  const isEmpty = computed(() => {
    if (result.value === null) return true
    return result.value.datasets.length === 0
  })

  watchEffect(async () => {
    // ── Touch reactive dependencies so Vue tracks them ────────────────────
    const config = widgetRef.value.config
    const displayCurrencyValue = displayCurrencyRef.value
    const primaryCurrency = settingsStore.primaryCurrency
    void exchangeRatesStore.rates.length
    void transactionsStore.transactions.length
    void transfersStore.transfers.length

    loading.value = true

    try {
      // ── Step 1: Resolve date range ────────────────────────────────────────
      const { time_range, filters, granularity, group_by, aggregation, category_groups } = config

      let dateFrom: string
      let dateTo: string

      if (time_range.type === 'dynamic') {
        const resolved = resolvePreset(time_range.value)
        dateFrom = resolved.from
        dateTo = resolved.to
      } else {
        dateFrom = time_range.value.from
        dateTo = time_range.value.to
      }

      // ── Step 2: Read and filter from IndexedDB ────────────────────────────
      const [allTxs, allAccounts, allCategories] = await Promise.all([
        db.transactions.toArray(),
        db.accounts.toArray(),
        db.categories.toArray(),
      ])

      // Build lookup maps
      const accountMap = new Map<string, LocalAccount>()
      for (const acc of allAccounts) {
        accountMap.set(acc.id, acc)
      }

      const categoryMap = new Map<string, LocalCategory>()
      for (const cat of allCategories) {
        categoryMap.set(cat.id, cat)
      }

      // Build category-to-group reverse map
      const categoryToGroup = new Map<string, string>()
      if (category_groups) {
        for (const [label, ids] of Object.entries(category_groups)) {
          for (const id of ids) {
            categoryToGroup.set(id, label)
          }
        }
      }

      // Filter transactions
      const filteredTxs = (allTxs as LocalTransaction[]).filter((tx) => {
        // Date range filter
        if (tx.date < dateFrom || tx.date > dateTo) return false

        // Account filter
        if (filters.account_ids && filters.account_ids.length > 0) {
          if (!filters.account_ids.includes(tx.account_id)) return false
        }

        // Category filter
        if (filters.category_ids && filters.category_ids.length > 0) {
          if (!tx.category_id || !filters.category_ids.includes(tx.category_id)) return false
        }

        // Type filter
        if (filters.type) {
          if (tx.type !== filters.type) return false
        }

        // Amount range filters
        const amount = Number(tx.amount)
        if (filters.amount_min != null && amount < filters.amount_min) return false
        if (filters.amount_max != null && amount > filters.amount_max) return false

        return true
      })

      // ── Step 3: Currency conversion ───────────────────────────────────────
      function convertAmount(tx: LocalTransaction): number {
        const account = accountMap.get(tx.account_id)
        const raw = Number(tx.amount)

        if (!account || account.currency === primaryCurrency) {
          // Already in primary currency — skip step 1
          if (displayCurrencyValue === primaryCurrency) return raw
          return raw * (exchangeRatesStore.getRate(primaryCurrency, displayCurrencyValue) ?? 1)
        }

        // Step 1: account currency -> primaryCurrency using historical base_rate
        const rate = (tx.base_rate != null && tx.base_rate !== 0)
          ? Number(tx.base_rate)
          : (exchangeRatesStore.getRate(account.currency, primaryCurrency) ?? 1)
        const primaryAmount = raw * rate

        // Step 2: primaryCurrency -> displayCurrency using current rate
        if (displayCurrencyValue === primaryCurrency) return primaryAmount
        return primaryAmount * (exchangeRatesStore.getRate(primaryCurrency, displayCurrencyValue) ?? 1)
      }

      // ── Step 4 & 5: Assign bucket and group key ──────────────────────────
      function getGroupKey(tx: LocalTransaction): string {
        switch (group_by) {
          case 'category': {
            const fromGroup = tx.category_id ? categoryToGroup.get(tx.category_id) : undefined
            return fromGroup ?? categoryMap.get(tx.category_id ?? '')?.name ?? 'Sin categoría'
          }
          case 'account':
            return accountMap.get(tx.account_id)?.name ?? 'Desconocida'
          case 'type':
            return tx.type
          case 'day_of_week':
            return DAY_NAMES[new Date(tx.date + 'T12:00:00').getDay()]
          case 'none':
            return 'Total'
          default:
            return 'Total'
        }
      }

      // ── Step 6: Collect data ──────────────────────────────────────────────
      // Structure: Map<groupKey, Map<bucket, number[]>>
      const collected = new Map<string, Map<string, number[]>>()

      for (const tx of filteredTxs) {
        const gk = getGroupKey(tx)
        const bucket = group_by === 'day_of_week' ? '_' : assignBucket(tx.date, granularity)
        const converted = convertAmount(tx)

        let groupMap = collected.get(gk)
        if (!groupMap) {
          groupMap = new Map<string, number[]>()
          collected.set(gk, groupMap)
        }

        let bucketValues = groupMap.get(bucket)
        if (!bucketValues) {
          bucketValues = []
          groupMap.set(bucket, bucketValues)
        }

        bucketValues.push(converted)
      }

      // ── Step 7 & 8: Aggregate and format result ───────────────────────────
      if (group_by === 'day_of_week') {
        // day_of_week: labels are weekday names that have data, ordered Mon-Sun
        const groupsWithData = new Set(collected.keys())
        const labels = DAY_NAMES_ORDERED.filter((name) => groupsWithData.has(name))

        // Build datasets, omitting groups with all-zero aggregated values
        const datasets: { label: string; data: number[] }[] = []
        for (const dayName of labels) {
          const groupMap = collected.get(dayName)
          const values = groupMap?.get('_') ?? []
          const aggregated = aggregate(values, aggregation)

          // Omit groups where the aggregated value is 0
          if (aggregated !== 0) {
            datasets.push({
              label: dayName,
              data: [aggregated],
            })
          }
        }

        result.value = {
          labels,
          datasets,
          totals: buildTotals(collected, aggregation),
          metadata: {
            date_from: dateFrom,
            date_to: dateTo,
            granularity,
            display_currency: displayCurrencyValue,
          },
        }
      } else {
        // Standard time-series: labels are sorted bucket keys
        const allBuckets = new Set<string>()
        for (const groupMap of collected.values()) {
          for (const bucket of groupMap.keys()) {
            allBuckets.add(bucket)
          }
        }
        const labels = Array.from(allBuckets).sort()

        // Build datasets, omitting groups with all-zero aggregated values
        const datasets: { label: string; data: number[] }[] = []
        for (const [gk, groupMap] of collected) {
          const data = labels.map((label) => {
            const values = groupMap.get(label) ?? []
            return aggregate(values, aggregation)
          })

          // Omit groups where every value is 0
          if (data.some((v) => v !== 0)) {
            datasets.push({ label: gk, data })
          }
        }

        result.value = {
          labels,
          datasets,
          totals: buildTotals(collected, aggregation),
          metadata: {
            date_from: dateFrom,
            date_to: dateTo,
            granularity,
            display_currency: displayCurrencyValue,
          },
        }
      }
    } catch (err) {
      console.error('[useWidgetData] computation failed:', err)
      result.value = null
    } finally {
      loading.value = false
    }
  })

  return { result, loading, isEmpty }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Build a totals record: group key → single aggregate across ALL raw values
 * in that group (not a second-pass aggregate of bucket aggregates).
 * For 'sum': grand total. For 'avg': mean of every individual value.
 * For 'count': total transaction count. For 'min'/'max': global extremes.
 */
function buildTotals(
  collected: Map<string, Map<string, number[]>>,
  aggregation: Aggregation
): Record<string, number> {
  const totals: Record<string, number> = {}
  for (const [gk, groupMap] of collected) {
    const allValues: number[] = []
    for (const values of groupMap.values()) {
      allValues.push(...values)
    }
    totals[gk] = aggregate(allValues, aggregation)
  }
  return totals
}
