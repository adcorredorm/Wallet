/**
 * useNetWorthHistory — Net worth evolution composable
 *
 * Computes a time-series of net worth data points entirely from IndexedDB
 * (Dexie) — no backend endpoint is involved.
 *
 * Algorithm overview:
 * 1. Read all transactions, transfers, and accounts from IndexedDB.
 * 2. Build a unified chronological event stream (one event per transaction,
 *    two events per transfer: source debit + destination credit).
 * 3. Walk ALL events from the beginning of time, maintaining a running balance
 *    Map<account_id, number> in each account's native currency.
 * 4. At each boundary date (by the selected granularity) that falls within the
 *    output range, convert each account balance to primaryCurrency using the
 *    most recent base_rate seen for that account (falling back to
 *    exchangeRatesStore.getRate(), then to 1 as a last resort).
 * 5. Emit { date, value }[] data points.
 *
 * Why process ALL events (not just in-range ones)?
 * The running balance must reflect the full account history to give correct
 * opening balances at the start of the selected range. A balance-only view
 * of the selected period would start from 0, which is misleading.
 *
 * base_rate semantics:
 * base_rate = units of primaryCurrency per 1 unit of account.currency at the
 * moment the event was recorded. Stored on the event at write time.
 * When null (created offline with no rate cache), falls back to
 * exchangeRatesStore.getRate(currency, primaryCurrency) at chart-render time.
 */

import { ref, computed, watchEffect, type Ref } from 'vue'
import {
  format,
  parseISO,
  subDays,
  addDays,
  startOfWeek,
  startOfMonth,
  startOfYear,
  addWeeks,
  addMonths,
  addYears,
  isBefore,
  isEqual
} from 'date-fns'
import { db } from '@/offline'
import type { LocalTransaction, LocalTransfer } from '@/offline'
import { useExchangeRatesStore } from '@/stores/exchangeRates'
import { useSettingsStore } from '@/stores/settings'
import { useTransactionsStore } from '@/stores/transactions'
import { useTransfersStore } from '@/stores/transfers'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type Granularity = 'day' | 'triday' | 'week' | 'month' | 'year'

export interface DataPoint {
  date: string   // ISO date string YYYY-MM-DD for the boundary
  value: number  // Net worth in primaryCurrency at this boundary
}

export interface UseNetWorthHistoryOptions {
  rangeDays?: Ref<number> | number  // defaults to 30
  granularity?: Ref<Granularity | null> | Granularity | null  // null = auto-select
  endDate?: string  // ISO date YYYY-MM-DD, defaults to today
}

export interface UseNetWorthHistoryReturn {
  dataPoints: Ref<DataPoint[]>
  loading: Ref<boolean>
  isEmpty: Ref<boolean>
  granularity: Ref<Granularity>
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Auto-select granularity from range size.
 * ≤7d   → day    (1S: 7 pts, 1 pt/day)
 * ≤30d  → triday (1M: ~10 pts, 1 pt/3 days)
 * ≤456d → month  (1A: 12 pts, YTD: ≤12 pts, Todo ≤15 months: ≤15 pts)
 * >456d → year   (Todo >15 months: 1 pt/year)
 */
function selectGranularity(days: number): Granularity {
  if (days <= 7) return 'day'
  if (days <= 30) return 'triday'
  if (days <= 456) return 'month'
  return 'year'
}

/**
 * Generate an array of boundary Date objects for the given range and granularity.
 *
 * For 'week', boundaries start on Monday (ISO week). For 'month' and 'year',
 * they start on the first day of the period. For 'day', every calendar day.
 *
 * The first boundary may be before startDate (e.g. the Monday before startDate)
 * so that the first output point always aligns to a clean boundary. Boundaries
 * after endDate are excluded.
 */
function generateBoundaries(
  startDate: Date,
  endDate: Date,
  granularity: Granularity
): Date[] {
  const boundaries: Date[] = []
  let cursor: Date
  let advance: (d: Date) => Date

  switch (granularity) {
    case 'day':
      cursor = new Date(startDate)
      advance = (d) => addDays(d, 1)
      break
    case 'triday':
      cursor = new Date(startDate)
      advance = (d) => addDays(d, 3)
      break
    case 'week':
      cursor = startOfWeek(startDate, { weekStartsOn: 1 })
      advance = (d) => addWeeks(d, 1)
      break
    case 'month':
      cursor = startOfMonth(startDate)
      advance = (d) => addMonths(d, 1)
      break
    case 'year':
      cursor = startOfYear(startDate)
      advance = (d) => addYears(d, 1)
      break
  }

  while (isBefore(cursor, endDate) || isEqual(cursor, endDate)) {
    boundaries.push(new Date(cursor))
    cursor = advance(cursor)
  }

  return boundaries
}

// ---------------------------------------------------------------------------
// Composable
// ---------------------------------------------------------------------------

export function useNetWorthHistory(
  options: UseNetWorthHistoryOptions = {}
): UseNetWorthHistoryReturn {
  const exchangeRatesStore = useExchangeRatesStore()
  const settingsStore = useSettingsStore()
  const transactionsStore = useTransactionsStore()
  const transfersStore = useTransfersStore()

  // Resolve reactive options to plain computed values
  const _rangeDays = computed<number>(() => {
    const raw = options.rangeDays
    if (raw === undefined) return 30
    return typeof raw === 'number' ? raw : raw.value
  })

  const _granularityOverride = computed<Granularity | null>(() => {
    const raw = options.granularity
    if (raw === undefined || raw === null) return null
    if (typeof raw === 'object' && 'value' in raw) return raw.value
    return raw as Granularity | null
  })

  const granularity = computed<Granularity>(() =>
    _granularityOverride.value ?? selectGranularity(_rangeDays.value)
  )

  const loading = ref(false)
  const _dataPoints = ref<DataPoint[]>([])
  // isEmpty is true when there are no financial events at all — not just when
  // all data points are 0 (which happens when accounts exist but transactions
  // don't). The component uses this to show the "register your first transaction"
  // empty state banner.
  const _hasEvents = ref(false)
  const isEmpty = computed(() => !_hasEvents.value)

  // watchEffect re-runs whenever any reactive dependency changes:
  // - _rangeDays (if passed as a Ref)
  // - granularity (derived from _rangeDays or override)
  // - settingsStore.primaryCurrency
  // - exchangeRatesStore.rates / exchangeRatesStore.loading
  watchEffect(async () => {
    // Read reactive dependencies explicitly so Vue tracks them
    const rangeDays = _rangeDays.value
    const gran = granularity.value
    const primaryCurrency = settingsStore.primaryCurrency

    // Guard: if exchange rates are still loading from IndexedDB on first boot,
    // skip this run and wait. This prevents the hard-refresh race condition where
    // watchEffect fires before fetchRates() resolves — without this guard, every
    // foreign-currency account would use rate=1, producing a wrong net worth chart.
    // Subscribing to exchangeRatesStore.loading here ensures watchEffect re-runs
    // automatically once loading transitions false → rates are available.
    if (exchangeRatesStore.loading) {
      loading.value = true
      return
    }

    // Touch rates.length to subscribe to rate updates — when rates refresh,
    // fallback rate lookups may change and the chart should recompute.
    void exchangeRatesStore.rates.length
    // Subscribe to transaction/transfer store updates so the chart recomputes
    // automatically when sync completes (refreshFromDB) or when the user adds
    // a new transaction. The composable reads from Dexie directly but needs
    // this reactive dep to know when Dexie has new data.
    void transactionsStore.transactions.length
    void transfersStore.transfers.length

    loading.value = true

    try {
      const [txs, transfers, accounts] = await Promise.all([
        db.transactions.toArray(),
        db.transfers.toArray(),
        db.accounts.toArray(),
      ])

      const endDateStr = options.endDate ?? format(new Date(), 'yyyy-MM-dd')
      const endDate = parseISO(endDateStr)
      const startDate = subDays(endDate, rangeDays - 1)

      // ── Build unified event stream ───────────────────────────────────────
      // Each event carries: date, created_at (for tiebreaking), account_id,
      // delta (signed native-currency amount), and optional base_rate.
      interface Event {
        date: string
        created_at: string
        account_id: string
        delta: number
        base_rate?: number | null  // undefined = no rate on this event type
      }

      const events: Event[] = []

      for (const tx of txs as LocalTransaction[]) {
        events.push({
          date: tx.date,
          created_at: tx.created_at ?? tx.date + 'T00:00:00Z',
          account_id: tx.account_id,
          delta: tx.type === 'income' ? Number(tx.amount) : -Number(tx.amount),
          base_rate: tx.base_rate,
        })
      }

      for (const tr of transfers as LocalTransfer[]) {
        const trCreatedAt = tr.created_at ?? tr.date + 'T00:00:00Z'
        // Source side: debit — carries the source account's base_rate
        events.push({
          date: tr.date,
          created_at: trCreatedAt,
          account_id: tr.source_account_id,
          delta: -Number(tr.amount),
          base_rate: tr.base_rate,
        })
        // Destination side: credit at destination_amount (same-currency → amount)
        // base_rate is undefined here — the destination account's rate comes from
        // its own transaction events. undefined means "don't update lastRates for
        // this account on the destination event".
        events.push({
          date: tr.date,
          created_at: trCreatedAt,
          account_id: tr.destination_account_id,
          delta: Number(tr.destination_amount ?? tr.amount),
          base_rate: undefined,
        })
      }

      // Sort ascending: date first, created_at as tiebreaker
      events.sort((a, b) => {
        const byDate = a.date.localeCompare(b.date)
        if (byDate !== 0) return byDate
        return a.created_at.localeCompare(b.created_at)
      })

      // ── Generate output boundary dates ───────────────────────────────────
      const boundaries = generateBoundaries(startDate, endDate, gran)
      const boundaryStrs = boundaries.map(d => format(d, 'yyyy-MM-dd'))

      // Track whether any financial events exist so isEmpty can be computed correctly.
      _hasEvents.value = events.length > 0

      // Short-circuit: no events means no meaningful data points to show.
      if (events.length === 0) {
        _dataPoints.value = []
        return
      }

      // ── Walking pass ─────────────────────────────────────────────────────
      // balances: native-currency running balance per account
      // lastRates: most recent base_rate seen per account (updated when the
      //            event has a defined base_rate field, even if null)
      const balances = new Map<string, number>()
      const lastRates = new Map<string, number | null>()

      const result: DataPoint[] = []
      let eventIdx = 0
      const totalEvents = events.length

      const startDateStr = format(startDate, 'yyyy-MM-dd')

      for (const boundaryStr of boundaryStrs) {
        // Process all events with date <= current boundary
        while (eventIdx < totalEvents && events[eventIdx].date <= boundaryStr) {
          const ev = events[eventIdx]

          // Update running balance
          balances.set(ev.account_id, (balances.get(ev.account_id) ?? 0) + ev.delta)

          // Update lastRates only when the event carries a base_rate field
          // (undefined = destination side of transfer, don't update)
          if ('base_rate' in ev && ev.base_rate !== undefined) {
            // ev.base_rate can be a number (captured rate) or null (offline)
            lastRates.set(ev.account_id, ev.base_rate as number | null)
          }

          eventIdx++
        }

        // Only emit data points within the output range
        if (boundaryStr >= startDateStr && boundaryStr <= endDateStr) {
          let netWorth = 0

          for (const [accountId, balance] of balances) {
            const account = accounts.find(a => a.id === accountId)
            if (!account) continue

            // Effective rate priority:
            // 1. Captured base_rate from the most recent event for this account
            // 2. Live rate from exchangeRatesStore.getRate() (current rates)
            // 3. 1 as absolute last resort (treats currency as equal to primary)
            let effectiveRate: number | null = lastRates.has(accountId)
              ? lastRates.get(accountId)!
              : null

            if (effectiveRate === null) {
              effectiveRate = exchangeRatesStore.getRate(
                account.currency,
                primaryCurrency
              )
            }

            netWorth += balance * (effectiveRate ?? 1)
          }

          result.push({ date: boundaryStr, value: netWorth })
        }
      }

      _dataPoints.value = result
    } catch (err) {
      console.error('[useNetWorthHistory] computation failed:', err)
      _dataPoints.value = []
      _hasEvents.value = false
    } finally {
      loading.value = false
    }
  })

  return {
    dataPoints: _dataPoints,
    loading,
    isEmpty,
    granularity
  }
}
