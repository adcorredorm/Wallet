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
 *    output range, convert each account balance to primaryCurrency using
 *    exchangeRatesStore.getRate(account.currency, primaryCurrency), falling
 *    back to 1 if no rate is cached (offline cold-start).
 * 5. Emit { date, value }[] data points.
 *
 * Why process ALL events (not just in-range ones)?
 * The running balance must reflect the full account history to give correct
 * opening balances at the start of the selected range. A balance-only view
 * of the selected period would start from 0, which is misleading.
 *
 * Currency conversion:
 * Always uses exchangeRatesStore.getRate(account.currency, primaryCurrency) so
 * the chart respects the user's current primary currency. Falls back to 1 if
 * no rate is cached (offline cold-start). Historical base_rate from events is
 * not used — it was denominated in the primaryCurrency at the time of creation,
 * making it incorrect when the user changes their primary currency.
 *
 * Debounce strategy:
 * The watchEffect wrapper reads all reactive deps synchronously (so Vue tracks
 * them) and then delegates the heavy IndexedDB work to a debounced function
 * (300ms). This prevents excessive re-computations when multiple reactive deps
 * change in rapid succession (e.g. initial store hydration).
 *
 * Guard 2 timeout:
 * syncTimedOut flips after 15s — allowing the chart to unblock even if the
 * backend sync never completes or completes without transitioning isSyncing→false.
 */

import { ref, computed, watchEffect, onScopeDispose, type Ref } from 'vue'
import { useDebounceFn } from '@vueuse/core'
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
import { useSyncStore } from '@/stores/sync'

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
 * ≤7d  → day    (1S: 7 pts, 1 pt/day)
 * ≤30d → triday (1M: ~10 pts, 1 pt/3 days)
 * ≤730d → month (1A: 12 pts, YTD: ≤12 pts, Todo short: ~15 pts)
 * >730d → year
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

  // Ensure endDate is always the final boundary.
  // Without this, events between the last period boundary and endDate
  // (e.g. March 2–17 when granularity='month') are never accumulated.
  if (boundaries.length === 0 || !isEqual(boundaries[boundaries.length - 1], endDate)) {
    boundaries.push(new Date(endDate))
  }

  return boundaries
}

// ---------------------------------------------------------------------------
// Composable
// ---------------------------------------------------------------------------

// How long to wait before unblocking Guard 2 regardless of sync state.
// This prevents the skeleton from being shown indefinitely if the backend
// never responds or never transitions isSyncing to false.
const SYNC_SKELETON_TIMEOUT_MS = 15_000

export function useNetWorthHistory(
  options: UseNetWorthHistoryOptions = {}
): UseNetWorthHistoryReturn {
  const exchangeRatesStore = useExchangeRatesStore()
  const settingsStore = useSettingsStore()
  const transactionsStore = useTransactionsStore()
  const transfersStore = useTransfersStore()
  const syncStore = useSyncStore()

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

  // Guard 2 safety valve: flip after 15s so the chart can unblock even if the
  // sync never completes. Set once on composable creation (outside watchEffect)
  // so the timer is not reset on every reactive re-run.
  const syncTimedOut = ref(false)
  const syncTimeoutId = setTimeout(() => { syncTimedOut.value = true }, SYNC_SKELETON_TIMEOUT_MS)
  onScopeDispose(() => clearTimeout(syncTimeoutId))

  // ---------------------------------------------------------------------------
  // Debounced computation
  // ---------------------------------------------------------------------------
  // runComputation receives all reactive values as plain parameters.
  // It must NOT read reactive refs directly — it is called from a debounced
  // context where Vue's dependency tracking is no longer active.
  // All reactive tracking happens in the synchronous watchEffect wrapper below.
  const runComputation = useDebounceFn(async (
    rangeDays: number,
    gran: Granularity,
    primaryCurrency: string,
  ) => {
    try {
      const [txs, transfers, accounts] = await Promise.all([
        db.transactions.toArray(),
        db.transfers.toArray(),
        db.accounts.toArray(),
      ])

      // options.endDate is a plain string | undefined (non-reactive), so reading it
      // directly as a closure is safe here. If this is ever upgraded to a Ref<string>,
      // it must be passed as a parameter to maintain the "no reactive reads inside
      // runComputation" contract.
      const endDateStr = options.endDate ?? format(new Date(), 'yyyy-MM-dd')
      const endDate = parseISO(endDateStr)
      const startDate = subDays(endDate, rangeDays - 1)

      // ── Build unified event stream ───────────────────────────────────────
      // Each event carries: date, created_at (for tiebreaking), account_id,
      // and delta (signed native-currency amount).
      interface Event {
        date: string
        created_at: string
        account_id: string
        delta: number
      }

      const events: Event[] = []

      for (const tx of txs as LocalTransaction[]) {
        events.push({
          date: tx.date,
          created_at: tx.created_at ?? tx.date + 'T00:00:00Z',
          account_id: tx.account_id,
          delta: tx.type === 'income' ? Number(tx.amount) : -Number(tx.amount),
        })
      }

      for (const tr of transfers as LocalTransfer[]) {
        const trCreatedAt = tr.created_at ?? tr.date + 'T00:00:00Z'
        // Source side: debit
        events.push({
          date: tr.date,
          created_at: trCreatedAt,
          account_id: tr.source_account_id,
          delta: -Number(tr.amount),
        })
        // Destination side: credit at destination_amount (same-currency → amount)
        events.push({
          date: tr.date,
          created_at: trCreatedAt,
          account_id: tr.destination_account_id,
          delta: Number(tr.destination_amount ?? tr.amount),
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
      const balances = new Map<string, number>()

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

          eventIdx++
        }

        // Only emit data points within the output range
        if (boundaryStr >= startDateStr && boundaryStr <= endDateStr) {
          let netWorth = 0

          for (const [accountId, balance] of balances) {
            const account = accounts.find(a => a.id === accountId)
            if (!account) continue

            // Always use current rates for the active primaryCurrency.
            // Historical base_rate is denominated in the primaryCurrency at the
            // time the transaction was created — using it when primaryCurrency
            // changes would apply rates from the wrong currency.
            // Fallback to 1 if no rate is cached (offline cold-start).
            const effectiveRate = exchangeRatesStore.getRate(
              account.currency,
              primaryCurrency
            )

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
  }, 300)

  // ---------------------------------------------------------------------------
  // Synchronous watchEffect wrapper
  // ---------------------------------------------------------------------------
  // Reads ALL reactive dependencies here so Vue tracks them. Passes the current
  // values as plain parameters to runComputation so the debounced function never
  // needs to access reactive state directly (which would be outside the tracking
  // context once the debounce delay fires).
  watchEffect(() => {
    // Read ALL reactive deps:
    const rangeDays = _rangeDays.value
    const gran = granularity.value
    const primaryCurrency = settingsStore.primaryCurrency

    // Read unconditionally so Vue tracks these deps even when Guard 1 would have
    // blocked. Guard 1 has been removed — rates are seeded via BASE_RATES on
    // cold start. These reads keep Vue tracking for background sync updates.
    // void suppresses TS6133 "declared but never read".
    void exchangeRatesStore.loading
    void exchangeRatesStore.rates.length

    // Subscribe to sync state: re-run when isSyncing or initialSyncComplete
    // transitions so the chart recomputes with fresh IndexedDB data after sync.
    const isSyncing = syncStore.isSyncing
    const initialSyncComplete = syncStore.initialSyncComplete

    // Read unconditionally so Vue tracks these deps in all watchEffect executions.
    const txCount = transactionsStore.transactions.length
    const tfCount = transfersStore.transfers.length

    // Read syncTimedOut inside watchEffect so Vue tracks it as a dependency.
    // When the setTimeout fires and flips syncTimedOut.value, watchEffect re-runs
    // and Guard 2 is bypassed, unblocking the skeleton after 15s.
    const timedOut = syncTimedOut.value

    // Guard 2: show skeleton only on first sync when Dexie has no data.
    // Condition: not yet completed initial sync, sync in progress, no cached
    // data from previous sessions, and timeout has not fired yet.
    // If timedOut=true → fall through and render empty state.
    if (!initialSyncComplete && isSyncing && txCount === 0 && tfCount === 0 && !timedOut) {
      loading.value = true
      return
    }

    // Signal loading before debounced computation so the skeleton shows
    // immediately on dep change rather than only after the 300ms debounce fires.
    loading.value = true
    void runComputation(rangeDays, gran, primaryCurrency)
  })

  return {
    dataPoints: _dataPoints,
    loading,
    isEmpty,
    granularity
  }
}
