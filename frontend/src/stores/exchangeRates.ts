/**
 * Exchange Rates Store
 *
 * Manages cached foreign-exchange rates following the same offline-first
 * stale-while-revalidate pattern used by the accounts store.
 *
 * Why NOT use fetchAllWithRevalidation from @/offline/repository?
 * That generic helper requires TServer extends { id: string; updated_at: string }.
 * LocalExchangeRate has no `id` or `updated_at` — its PK is `currency_code`
 * and the recency field is `fetched_at`. Forcing a mismatched generic would
 * require brittle type casts. Instead, this store implements the same three-step
 * SWR pattern directly, which is cleaner and easier to understand.
 *
 * Why no PendingMutation queue for exchange rates?
 * Exchange rates are read-only from the frontend's perspective. The server
 * fetches them from external sources (exchangerate.host, CoinGecko) and the
 * frontend only caches the result. There is nothing to sync back.
 *
 * Rate arithmetic reference:
 *   LocalExchangeRate.rate_to_usd = units of this currency per 1 USD.
 *   Example: USD rate_to_usd = 1, COP rate_to_usd = 4200, EUR rate_to_usd = 0.92
 *   To convert amount_A (in currency A) to currency B:
 *     amount_B = amount_A * (rate_to_usd_B / rate_to_usd_A)
 *   Because: amount_A / rate_to_usd_A = amount in USD, * rate_to_usd_B = amount in B.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useOnline } from '@vueuse/core'
import { db } from '@/offline'
import type { LocalExchangeRate } from '@/offline'
import { fetchExchangeRates } from '@/api/exchangeRates'
import { formatCurrency } from '@/utils/formatters'

// Shared online indicator — VueUse returns the same Ref<boolean> on every
// call, so this is not a second subscription.
const isOnline = useOnline()

/**
 * BASE_RATES — fallback exchange rates seeded on first launch.
 *
 * Why seed these into Dexie on cold start?
 * On a user's very first session (or after clearing IndexedDB), the exchange
 * rates table is empty. Without seeding, useNetWorthHistory would show every
 * multi-currency account as "no rate found" and fall back to rate=1, which
 * produces wildly incorrect net worth numbers until the network sync runs.
 * Seeding reasonable approximations ensures the UI is immediately useful
 * even before the first successful backend sync.
 *
 * Why source: 'system'?
 * Differentiates these seeded records from network-fetched ones
 * ('exchangerate.host', 'coingecko'). The sync process will overwrite
 * them with fresh rates on first successful online sync.
 *
 * Rates captured: 2026-03-16. On every minor version release, ask the user
 * whether to refresh these values with current DB rates.
 */
const BASE_RATES: LocalExchangeRate[] = [
  { currency_code: 'USD', rate_to_usd: 1,              fetched_at: '2026-03-16T00:00:00Z', source: 'system', updated_at: '2026-03-16T00:00:00Z' },
  { currency_code: 'COP', rate_to_usd: 3691.6733650,   fetched_at: '2026-03-16T00:00:00Z', source: 'system', updated_at: '2026-03-16T00:00:00Z' },
  { currency_code: 'EUR', rate_to_usd: 0.8746440,      fetched_at: '2026-03-16T00:00:00Z', source: 'system', updated_at: '2026-03-16T00:00:00Z' },
  { currency_code: 'BRL', rate_to_usd: 5.2654710,      fetched_at: '2026-03-16T00:00:00Z', source: 'system', updated_at: '2026-03-16T00:00:00Z' },
  { currency_code: 'JPY', rate_to_usd: 159.5572970,    fetched_at: '2026-03-16T00:00:00Z', source: 'system', updated_at: '2026-03-16T00:00:00Z' },
  { currency_code: 'ARS', rate_to_usd: 1452.2500000,   fetched_at: '2026-03-16T00:00:00Z', source: 'system', updated_at: '2026-03-16T00:00:00Z' },
  { currency_code: 'GBP', rate_to_usd: 0.7553490,      fetched_at: '2026-03-16T00:00:00Z', source: 'system', updated_at: '2026-03-16T00:00:00Z' },
  { currency_code: 'BTC', rate_to_usd: 0.0000135619,   fetched_at: '2026-03-16T00:00:00Z', source: 'system', updated_at: '2026-03-16T00:00:00Z' },
  { currency_code: 'ETH', rate_to_usd: 0.0004412634,   fetched_at: '2026-03-16T00:00:00Z', source: 'system', updated_at: '2026-03-16T00:00:00Z' },
]

export const useExchangeRatesStore = defineStore('exchangeRates', () => {
  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------

  // Reactive cache of all rates currently held in IndexedDB.
  const rates = ref<LocalExchangeRate[]>([])

  // True only during the initial IndexedDB read and the blocking first-load
  // path. Background revalidation never sets loading to true — it is silent.
  const loading = ref(false)

  // Populated when both IndexedDB and the network fail simultaneously.
  // A background revalidation failure alone does NOT set error — the cached
  // data is still valid and the UI should keep showing it.
  const error = ref<string | null>(null)

  // ISO timestamp of the most recent fetched_at across all cached rates.
  // Derived from state so it is always consistent with whatever is in rates[].
  const lastUpdated = computed<string | null>(() => {
    if (rates.value.length === 0) return null
    // Lexicographic comparison works correctly for ISO 8601 timestamps.
    return rates.value.reduce<string | null>((latest, r) => {
      if (!latest) return r.fetched_at
      return r.fetched_at > latest ? r.fetched_at : latest
    }, null)
  })

  // ---------------------------------------------------------------------------
  // Internal helpers
  // ---------------------------------------------------------------------------

  /**
   * Look up a rate by ISO 4217 code. Returns undefined when not cached.
   * Used internally by convert(), getRate(), and getRateDisplay().
   */
  function _findRate(currencyCode: string | undefined | null): LocalExchangeRate | undefined {
    if (!currencyCode) return undefined
    return rates.value.find(r => r.currency_code === currencyCode.toUpperCase())
  }

  // ---------------------------------------------------------------------------
  // Actions — Reads (offline-first, stale-while-revalidate)
  // ---------------------------------------------------------------------------

  /**
   * Load exchange rates using stale-while-revalidate with BASE_RATES seeding.
   *
   * Step 1 — Read from IndexedDB immediately.
   *           If Dexie is empty (cold start), seed BASE_RATES via bulkPut
   *           so the UI has reasonable approximations before the first sync.
   *           If Dexie fails entirely, fall back to BASE_RATES in-memory so
   *           currency conversion is never completely broken.
   *
   * Step 2 — Fire a background network request when online.
   *           On success: upsert every rate into IndexedDB via put() and
   *           update the reactive state so the UI reflects fresh data without
   *           a page reload.
   *           On network failure: the cached Dexie data (or BASE_RATES fallback)
   *           remains in rates[]. error is only set when rates are completely
   *           empty after all paths are exhausted.
   */
  async function fetchRates(): Promise<void> {
    loading.value = true
    error.value = null

    try {
      // Step 1 — Synchronous-feeling local read.
      let localData = await db.exchangeRates.toArray()

      // Cold start: seed BASE_RATES into Dexie so conversion is immediately
      // available, even before the first successful background network sync.
      if (localData.length === 0) {
        await db.exchangeRates.bulkPut(BASE_RATES)
        localData = BASE_RATES
      }

      rates.value = localData
    } catch (err: any) {
      // IndexedDB failure is unusual but should not crash the app.
      // Fall back to BASE_RATES in-memory so the conversion helpers work.
      console.warn('[exchangeRates] IndexedDB read failed:', err)
      rates.value = BASE_RATES
    } finally {
      loading.value = false
    }

    // Step 2 — Background revalidation (fire-and-forget, only when online).
    if (!isOnline.value) return

    ;(async () => {
      try {
        const response = await fetchExchangeRates()
        const freshRates = response.rates ?? []

        // Upsert each rate. db.exchangeRates.put() is both INSERT and UPDATE
        // because currency_code is the primary key — no duplicate-rate risk.
        for (const rate of freshRates) {
          await db.exchangeRates.put(rate)
        }

        // Re-read from IndexedDB after all puts so the reactive state reflects
        // exactly what is stored locally (same strategy as fetchAllWithRevalidation
        // using table.toArray() after bulkPut).
        const updatedLocal = await db.exchangeRates.toArray()
        rates.value = updatedLocal
      } catch (networkErr: any) {
        // Background revalidation failure: keep whatever IndexedDB had.
        // Only escalate to error if we have nothing cached at all.
        if (rates.value.length === 0) {
          error.value = networkErr.message || 'Error al cargar tipos de cambio'
        }
        console.warn('[exchangeRates] Background revalidation failed:', networkErr)
      }
    })()
  }

  // ---------------------------------------------------------------------------
  // Conversion helpers
  // ---------------------------------------------------------------------------

  /**
   * Convert an amount from one currency to another by triangulating via USD.
   *
   * Formula: amount_B = amount_A * (rate_to_usd_B / rate_to_usd_A)
   *
   * Graceful degradation: returns the original amount unchanged if either
   * currency is not in the cache. This means the UI shows the raw number
   * rather than crashing or returning NaN.
   *
   * @param amount       - Positive number (amounts are always positive per arch rules)
   * @param fromCurrency - ISO 4217 source currency code (e.g. 'COP')
   * @param toCurrency   - ISO 4217 target currency code (e.g. 'USD')
   */
  function convert(amount: number, fromCurrency: string | undefined | null, toCurrency: string | undefined | null): number {
    if (!fromCurrency || !toCurrency) return amount
    const from = fromCurrency.toUpperCase()
    const to = toCurrency.toUpperCase()

    // Identity shortcut — avoids any floating-point noise.
    if (from === to) return amount

    const fromRate = _findRate(from)
    const toRate = _findRate(to)

    // Graceful degradation: one or both currencies not cached.
    if (!fromRate || !toRate) return amount

    // Triangulate via USD.
    // rate_to_usd is units of currency per 1 USD, so:
    //   amount / fromRate.rate_to_usd = amount in USD
    //   * toRate.rate_to_usd          = amount in target currency
    return amount * (toRate.rate_to_usd / fromRate.rate_to_usd)
  }

  /**
   * Returns how many toCurrency units equal 1 fromCurrency.
   * Returns null if either currency is missing from the cache.
   *
   * Example: getRate('USD', 'COP') → 4200
   *          getRate('COP', 'USD') → 0.000238...
   */
  function getRate(fromCurrency: string | undefined | null, toCurrency: string | undefined | null): number | null {
    if (!fromCurrency || !toCurrency) return null
    const from = fromCurrency.toUpperCase()
    const to = toCurrency.toUpperCase()

    if (from === to) return 1

    const fromRate = _findRate(from)
    const toRate = _findRate(to)

    if (!fromRate || !toRate) return null

    return toRate.rate_to_usd / fromRate.rate_to_usd
  }

  /**
   * Returns formatted bidirectional rate strings for display in the UI.
   *
   * Why two directions?
   * When a user is about to convert USD → COP they want to see both
   * "1 USD = 4,200.00 COP" and "1 COP = 0.000238 USD" to understand the
   * exchange in both directions without doing mental arithmetic.
   *
   * Why parseFloat(n.toFixed(10)).toString() for the rate numbers?
   * toFixed(10) gives us enough decimal precision for micro-rate currencies
   * (e.g. BTC/satoshi). parseFloat strips all trailing zeros so we never
   * render "0.0002380000" — only "0.000238".
   *
   * Why formatCurrency for the human-readable amount?
   * formatCurrency handles the locale-aware comma/dot formatting and the
   * currency symbol placement (e.g. "$4,200.00" vs "€4.200,00"), which
   * makes the string ready for direct rendering in any component.
   *
   * Returns null if either currency is missing from the cache.
   */
  function getRateDisplay(
    fromCurrency: string | undefined | null,
    toCurrency: string | undefined | null
  ): { forward: string; inverse: string } | null {
    if (!fromCurrency || !toCurrency) return null
    const from = fromCurrency.toUpperCase()
    const to = toCurrency.toUpperCase()

    if (from === to) {
      const unity = formatCurrency(1, to)
      return { forward: `1 ${from} = ${unity}`, inverse: `1 ${to} = ${formatCurrency(1, from)}` }
    }

    const forwardRate = getRate(from, to)
    const inverseRate = getRate(to, from)

    if (forwardRate === null || inverseRate === null) return null

    // Strip trailing zeros for compact display of very small/large rates.
    const forwardNum = parseFloat(forwardRate.toFixed(10)).toString()
    const inverseNum = parseFloat(inverseRate.toFixed(10)).toString()

    // Use formatCurrency for the final display string so currency symbols,
    // locale separators, and compact notation all apply automatically.
    const forwardDisplay = formatCurrency(parseFloat(forwardNum), to)
    const inverseDisplay = formatCurrency(parseFloat(inverseNum), from)

    return {
      forward: `1 ${from} = ${forwardDisplay}`,
      inverse: `1 ${to} = ${inverseDisplay}`
    }
  }

  // ---------------------------------------------------------------------------
  // Expose
  // ---------------------------------------------------------------------------

  return {
    // State
    rates,
    loading,
    error,
    // Computed
    lastUpdated,
    // Actions
    fetchRates,
    convert,
    getRate,
    getRateDisplay
  }
})
