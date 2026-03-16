/**
 * Settings Store
 *
 * Why a dedicated store for settings?
 * Settings are user-configurable state that must:
 *   1. Survive offline usage (stored in IndexedDB via Dexie).
 *   2. Sync to the backend when connectivity returns (mutation queue).
 *   3. Be reactive so any component that reads primaryCurrency re-renders
 *      immediately when the user changes it — without a page reload.
 *
 * This store follows the identical offline-first, stale-while-revalidate
 * pattern used by the accounts store: load IndexedDB first (zero-latency
 * cold start), then fetch from the API in the background and merge the
 * fresher server data into both IndexedDB and the reactive state.
 *
 * Why `Record<string, unknown>` for the in-memory state?
 * Settings are a heterogeneous bag of key/value pairs. Using a typed map
 * avoids the need for a separate reactive ref per setting and makes it
 * trivial to add new settings without touching the store internals.
 * Callers narrow the type at the point of use via getSetting<T>().
 *
 * Why not use the stale-while-revalidate pattern used by other stores?
 * Other stores revalidate typed arrays via bulkPut on a table whose rows share
 * a common shape (LocalAccount[], etc.). Settings are stored as individual rows
 * keyed by string (key = 'primary_currency'), not as an array of uniform
 * entities. The revalidation logic here is short enough to inline directly,
 * which is cleaner than forcing the settings shape into a generic helper.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { db, mutationQueue } from '@/offline'

import { fetchSettings } from '@/api/settings'

// ---------------------------------------------------------------------------
// Default values — used when Dexie is empty AND the API is unreachable.
// ---------------------------------------------------------------------------
const DEFAULTS: Record<string, unknown> = {
  primary_currency: 'COP'
}

// Regex that validates an ISO 4217 currency code (2–10 uppercase ASCII letters).
// Why 10 as the upper bound? Crypto tickers can exceed 3 chars (e.g. 'USDC',
// 'USDT') while staying well below 10. We allow some headroom without being
// overly permissive.
const CURRENCY_CODE_RE = /^[A-Z]{2,10}$/

export const useSettingsStore = defineStore('settings', () => {
  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------

  /**
   * In-memory mirror of the settings table.
   *
   * Why not a reactive() instead of ref()?
   * ref() gives us a single reactive root that Vue's reactivity system tracks
   * as one unit. reactive() unwraps nested refs and can lose reactivity when
   * the object is replaced in full. Because we replace the entire settings
   * object on a fresh API response (via Object.assign or spread), ref() is
   * the safer choice — Vue sees one root change rather than trying to diff
   * individual fields of a reactive proxy.
   */
  const settings = ref<Record<string, unknown>>({ ...DEFAULTS })
  const loading = ref(false)
  const error = ref<string | null>(null)

  // ---------------------------------------------------------------------------
  // Computed
  // ---------------------------------------------------------------------------

  /**
   * The user's chosen primary display currency.
   *
   * Why a computed instead of just settings.value['primary_currency']?
   * Computed properties are cached and memoized — Vue only re-evaluates when
   * settings.value changes. Components that import primaryCurrency directly
   * will re-render only when this specific value changes, not on every
   * unrelated settings update. It also gives a clean, typed access point.
   */
  const primaryCurrency = computed(
    () => (settings.value['primary_currency'] as string) ?? 'COP'
  )

  // ---------------------------------------------------------------------------
  // Actions — Reads
  // ---------------------------------------------------------------------------

  /**
   * Load settings using the stale-while-revalidate pattern.
   *
   * Step 1 — Read IndexedDB immediately (synchronous from the caller's
   *   perspective because Dexie resolves in < 1 ms on warm cache).
   *   This populates the store right away so the UI never shows a blank state.
   *
   * Step 2 — Fetch the latest settings from the API in the background.
   *   On success: upsert each key into IndexedDB, then update the reactive
   *   state. The UI refreshes silently without any loading spinner.
   *   On failure: the Dexie cache already populated the store in Step 1, so
   *   the user sees their last-known settings with no error shown.
   *
   * Step 3 — Fallback: if Dexie was empty AND the API failed, apply DEFAULTS
   *   so the app always has a valid primary_currency to work with.
   *
   * Why fire-and-forget for the background fetch?
   * main.ts calls loadSettings() during boot and does not await a network
   * response — that would delay the interactive app start. The background
   * fetch is a best-effort revalidation, not a blocking dependency.
   */
  async function loadSettings(): Promise<void> {
    loading.value = true
    error.value = null

    try {
      // ── Step 1: populate from IndexedDB ─────────────────────────────────
      const localRows = await db.settings.toArray()

      if (localRows.length > 0) {
        const fromLocal: Record<string, unknown> = {}
        for (const row of localRows) {
          fromLocal[row.key] = row.value
        }
        settings.value = fromLocal
      }

      // ── Step 2: background revalidation from the API ─────────────────────
      // We intentionally do NOT await this fetch inside the loading block.
      // The loading flag reflects only the IndexedDB read, which is instant.
      // The background fetch is fire-and-forget: it updates IndexedDB and the
      // reactive state when it completes, without affecting the loading flag.
      _revalidateFromApi(localRows.length === 0)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Error al cargar configuración'
      error.value = msg
    } finally {
      loading.value = false
    }
  }

  /**
   * Background fetch from the API. Runs concurrently with the UI mounting.
   *
   * @param applyDefaultsOnFailure — true only when IndexedDB was empty, so
   *   a network failure still gives the app working defaults.
   */
  async function _revalidateFromApi(applyDefaultsOnFailure: boolean): Promise<void> {
    try {
      const freshData = await fetchSettings()

      // Upsert each setting into Dexie so future cold-starts are fast.
      const now = new Date().toISOString()
      for (const [key, value] of Object.entries(freshData)) {
        await db.settings.put({
          key,
          value,
          updated_at: now,
          _sync_status: 'synced',
          _local_updated_at: now
        })
      }

      // Merge server data on top of the current reactive state.
      // We use spread rather than full replacement so any pending local
      // settings (written offline and not yet synced) are not overwritten by
      // a potentially stale server response.
      //
      // Why prefer local over server for 'pending' keys?
      // A pending setting was written by the user MORE RECENTLY than the
      // server's copy (the mutation hasn't synced yet). Overwriting it with
      // the server value would cause the UI to flicker back to the old value
      // mid-sync — a confusing regression. We keep the local value until the
      // mutation is confirmed by the server.
      const pendingKeys = new Set(
        (await db.settings.where('_sync_status').equals('pending').toArray())
          .map(row => row.key)
      )

      const merged: Record<string, unknown> = { ...settings.value }
      for (const [key, value] of Object.entries(freshData)) {
        if (!pendingKeys.has(key)) {
          merged[key] = value
        }
      }
      settings.value = merged
    } catch {
      // Network or server error — use Dexie cache (already applied in loadSettings)
      // or fall back to defaults if Dexie was also empty.
      if (applyDefaultsOnFailure) {
        settings.value = { ...DEFAULTS }
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Actions — Writes
  // ---------------------------------------------------------------------------

  /**
   * Change the user's primary display currency.
   *
   * Why validate with a regex before writing?
   * Writing an invalid currency code to IndexedDB and queueing it for sync
   * would cause a backend validation error that the sync engine would then
   * have to handle as a permanent error. Failing fast here is cheaper and
   * gives the caller an actionable error message.
   *
   * Offline-first write sequence:
   *   1. Validate the currency code format.
   *   2. Write to Dexie immediately — the source of truth survives a reload.
   *   3. Update the reactive state immediately — the UI reflects the change
   *      without a network round-trip (optimistic update).
   *   4. Enqueue a mutation — the SyncManager will PUT it to the API when
   *      connectivity is available.
   */
  async function setPrimaryCurrency(currency: string): Promise<void> {
    // ── Validation ───────────────────────────────────────────────────────────
    if (!currency || !CURRENCY_CODE_RE.test(currency)) {
      throw new Error(
        `Invalid currency code "${currency}". Must be 2–10 uppercase letters (e.g. "COP", "USD", "USDC").`
      )
    }

    loading.value = true
    error.value = null

    try {
      const now = new Date().toISOString()

      // ── Step 1: Write to IndexedDB ────────────────────────────────────────
      // db.settings.put() is an upsert: it creates the row if it doesn't exist
      // and replaces it if it does. This is the correct semantics for settings
      // because we never have a "create vs update" distinction — a setting
      // either exists or it doesn't.
      await db.settings.put({
        key: 'primary_currency',
        value: currency,
        updated_at: now,
        _sync_status: 'pending',
        _local_updated_at: now
      })

      // ── Step 2: Update reactive state (optimistic) ────────────────────────
      settings.value = { ...settings.value, primary_currency: currency }

      // ── Step 3: Enqueue mutation for backend sync ─────────────────────────
      // entity_id uses the setting key ('primary_currency') as the stable
      // identifier. Settings are not UUID-keyed entities — the key IS the ID.
      // The SyncManager will call updateSetting('primary_currency', value)
      // when processing this mutation.
      //
      // Why operation: 'update' and not 'create'?
      // Settings have upsert semantics on both the client (Dexie put()) and
      // the server (PUT /api/v1/settings/{key}). There is no meaningful
      // distinction between creating and updating a setting — the server
      // accepts the same endpoint for both. Using 'update' avoids triggering
      // the SyncManager's temp-ID resolution and create+delete cancellation
      // logic, which are irrelevant for settings.
      await mutationQueue.enqueue({
        entity_type: 'setting',
        entity_id: 'primary_currency',
        operation: 'update',
        payload: { key: 'primary_currency', value: currency }
      })
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Error al guardar configuración'
      error.value = msg
      throw err
    } finally {
      loading.value = false
    }
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  /**
   * Type-safe getter with fallback.
   *
   * Why a generic getter instead of individual computed properties per key?
   * New settings will be added as the product grows. A single generic getter
   * scales to any number of keys without modifying the store. Consumers
   * provide the expected type T and a default value, keeping the type
   * narrowing at the call site rather than scattered across the store.
   *
   * Example:
   *   const precision = settingsStore.getSetting<number>('display_precision', 2)
   */
  function getSetting<T>(key: string, defaultValue: T): T {
    const val = settings.value[key]
    if (val === undefined || val === null) return defaultValue
    return val as T
  }

  // ---------------------------------------------------------------------------
  // Expose
  // ---------------------------------------------------------------------------

  return {
    // State
    settings,
    loading,
    error,
    // Computed
    primaryCurrency,
    // Actions
    loadSettings,
    setPrimaryCurrency,
    getSetting
  }
})
