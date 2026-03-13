/**
 * Application Entry Point
 *
 * Why this structure?
 * - createApp(): Vue 3 initialization
 * - Pinia before router: Store must be available for route guards
 * - Import CSS: Global Tailwind styles
 * - SW registration after mount: The app must be in the DOM before the SW
 *   registration fires so that any update-prompt UI can be rendered.
 */

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { useRegisterSW } from 'virtual:pwa-register/vue'
import App from './App.vue'
import router from './router'
import './assets/css/main.css'

const app = createApp(App)

// Initialize Pinia store (must come before router)
const pinia = createPinia()
app.use(pinia)

// Initialize router
app.use(router)

// Mount application
app.mount('#app')

/**
 * Service Worker Registration (Phase 1 — offline app shell)
 *
 * Why registerType: 'prompt' (set in vite.config.js)?
 * The SW will NOT auto-update. Instead, `needRefresh` becomes true when a new
 * SW version is available. Phase 2 will build a UI component that reads
 * `needRefresh` and calls `updateServiceWorker()` when the user taps "Update".
 *
 * Why here and not inside a component?
 * SW registration is an app-level singleton concern. Placing it in a component
 * would risk registering multiple times or missing registration if that
 * component is never rendered.
 *
 * The reactive refs (needRefresh, updateServiceWorker) are intentionally
 * unused in Phase 1. They will be consumed by a PWAUpdatePrompt component
 * in Phase 2. TypeScript's noUnusedLocals rule is suppressed for these two
 * via the void operator so the build does not fail.
 */
const { needRefresh, updateServiceWorker } = useRegisterSW({
  onRegistered(registration) {
    console.log('[SW] Service Worker registrado correctamente.', registration)
  },
  onRegisterError(error) {
    console.error('[SW] Error al registrar el Service Worker:', error)
  }
})

// Suppress TS noUnusedLocals — these will be consumed in Phase 2.
void needRefresh
void updateServiceWorker

/**
 * Phase 4 — Offline sync initialisation
 *
 * Why here (after app.mount) and not inside a component?
 * The SyncManager is an app-level singleton concern, not a component concern.
 * Placing it here guarantees exactly one processQueue() is ever registered,
 * regardless of which routes the user visits. A component-based registration
 * would fire once per component mount and could register multiple watchers.
 *
 * Why check isOnline.value at boot?
 * The onOnline() watcher only fires on *transitions* (false → true). If the
 * device is already online when the app starts, no transition event fires and
 * the queue would never be processed until the next connectivity change. The
 * explicit boot-time check handles the "user opens the app with WiFi already
 * active and has queued mutations from a previous offline session" scenario.
 *
 * Why not import syncManager from '@/offline' (the barrel)?
 * We import directly from '@/offline/sync-manager' to avoid a circular
 * dependency: index.ts re-exports everything including sync-manager, and
 * sync-manager imports from api/* which import from '@/types'. Using the
 * barrel here is fine too — kept as direct import for explicit clarity.
 *
 * Note: useNetworkStatus() calls useOnline() internally. useOnline() is also
 * called inside repository.ts at module level. VueUse ensures both share the
 * exact same underlying Ref<boolean> — there is only one global listener.
 */
import { syncManager } from '@/offline/sync-manager'
import { useNetworkStatus } from '@/composables/useNetworkStatus'
import { useSyncStore } from '@/stores/sync'
import { useAccountsStore } from '@/stores/accounts'
import { useTransactionsStore } from '@/stores/transactions'
import { useTransfersStore } from '@/stores/transfers'
import { useCategoriesStore } from '@/stores/categories'
import { useSettingsStore } from '@/stores/settings'
import { useExchangeRatesStore } from '@/stores/exchangeRates'
import { useDashboardsStore } from '@/stores/dashboards'

const { isOnline, onOnline, onOffline } = useNetworkStatus()

/**
 * Phase 5 — Wire the sync store to network events.
 *
 * Why set it here and not inside the syncStore itself?
 * The syncStore is a plain Pinia store with no side effects. It does not know
 * about VueUse or navigator.onLine — it just holds state. main.ts is the
 * correct place to wire external signals (navigator.onLine events) into the
 * store, just as it wires syncManager.processQueue() to network transitions.
 *
 * Why syncStore.setOnline(isOnline.value) synchronously?
 * The onOnline / onOffline callbacks only fire on *transitions*. If the app
 * starts while already offline, no transition fires and syncStore.isOnline
 * would remain stuck at its initial navigator.onLine value. Setting it once
 * synchronously here guarantees the store reflects the true initial state.
 */
const syncStore = useSyncStore()
syncStore.setOnline(isOnline.value)

/**
 * Phase 3.3 — Load user settings at boot.
 *
 * Why here and not inside a component?
 * Settings (e.g. primary_currency) are needed by multiple components and
 * stores as soon as the app renders. Bootstrapping them here ensures they
 * are available before any component mounts, without requiring each
 * component to call loadSettings() defensively.
 *
 * Why fire-and-forget (no await)?
 * loadSettings() reads IndexedDB first, which is synchronous from the
 * caller's perspective (< 1 ms). The background API revalidation is
 * explicitly non-blocking. There is no reason to delay the app mount
 * for a settings fetch.
 */
const settingsStore = useSettingsStore()
settingsStore.loadSettings().catch((err) => {
  console.warn('[boot] Settings failed to load:', err)
})

const exchangeRatesStore = useExchangeRatesStore()
exchangeRatesStore.fetchRates().catch((err) => {
  console.warn('[boot] Exchange rates failed to load:', err)
})

onOnline(() => {
  syncStore.setOnline(true)
})

onOffline(() => {
  syncStore.setOnline(false)
})

// Process any mutations queued during a previous offline session.
if (isOnline.value) {
  syncManager.processQueue()
}

// Re-process the queue every time the device regains connectivity.
onOnline(() => {
  syncManager.processQueue()
})

// Trigger an immediate sync whenever a new mutation is enqueued while online.
// The SyncManager's `processing` flag prevents concurrent runs — extra calls
// while a sync is already in progress are silent no-ops.
window.addEventListener('wallet:mutation-queued', () => {
  if (isOnline.value) {
    syncManager.processQueue()
  }
})

// After the SyncManager completes a full sync cycle (queue flushed +
// fullReadSync written to IndexedDB), refresh all reactive stores from the
// fresh local data so the UI reflects the authoritative server state —
// including real IDs replacing temp-* IDs — without firing extra API calls.
window.addEventListener('wallet:sync-complete', () => {
  const accountsStore = useAccountsStore()
  const transactionsStore = useTransactionsStore()
  const transfersStore = useTransfersStore()
  const categoriesStore = useCategoriesStore()
  const dashboardsStore = useDashboardsStore()
  Promise.allSettled([
    accountsStore.refreshFromDB(),
    transactionsStore.refreshFromDB(),
    transfersStore.refreshFromDB(),
    categoriesStore.refreshFromDB(),
    dashboardsStore.refreshFromDB()
  ]).then(() => {
    // Recompute account balances from the complete local transaction history.
    // After fullReadSync, IndexedDB has all transactions from the server so
    // the computed total is authoritative. We never call the /balance API
    // endpoint here — the frontend is a standalone app that uses IndexedDB
    // as its single source of truth for all displayed data.
    accountsStore.recomputeBalancesFromTransactions().catch(() => {})
  })
})
