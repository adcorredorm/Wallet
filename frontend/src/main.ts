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
import { useAuthStore } from '@/stores/auth'
import { useSettingsStore } from '@/stores/settings'
import { useExchangeRatesStore } from '@/stores/exchangeRates'
import { getSyncEnabled } from '@/offline/auth-db'

const app = createApp(App)

// Initialize Pinia store (must come before router)
const pinia = createPinia()
app.use(pinia)

// Initialize router
app.use(router)

/**
 * Silent session restore at boot.
 *
 * Por qué await aquí antes de mount?
 * Si montáramos primero y luego llamáramos initializeFromStorage(), habría un
 * frame donde el router ya evaluó los guards con isAuthenticated === false
 * (antes de que el refresh silencioso completara). Eso provocaría un redirect
 * no deseado a /login aunque el usuario tenga un refresh_token válido.
 * Esperamos el resultado antes de montar para que el primer render ya tenga
 * el estado de auth correcto. El impacto en tiempo de arranque es mínimo:
 * IndexedDB es local y el refresh es una llamada HTTP única.
 *
 * Por qué no bloqueamos si falla?
 * initializeFromStorage() maneja sus propios errores internamente (refresh()
 * captura excepciones y devuelve false). La app siempre arranca — en el peor
 * caso lo hace en modo invitado.
 */
const authStore = useAuthStore()

// Initialized here so the .then() callback below can reference them.
// API calls are deferred until after initializeFromStorage() completes —
// see comment inside the .then() for why.
const settingsStore = useSettingsStore()
const exchangeRatesStore = useExchangeRatesStore()

// Silent session restore before mount — using .then() instead of top-level
// await for compatibility with the es2020 build target.
authStore.initializeFromStorage().then(() => {
  app.mount('#app')

  // Load settings and exchange rates AFTER auth is initialized.
  // These calls make API requests that require a valid access token.
  // Running them before initializeFromStorage() completes causes two
  // concurrent authStore.refresh() calls with the same refresh token —
  // one succeeds and rotates the token, the other fails and clears auth state.
  // Both still read from IndexedDB first (< 1ms) so UI data is available
  // immediately; only the background API revalidation is delayed.
  settingsStore.loadSettings().catch((err) => {
    console.warn('[boot] Settings failed to load:', err)
  })
  exchangeRatesStore.fetchRates().catch((err) => {
    console.warn('[boot] Exchange rates failed to load:', err)
  })

  // Restore error count from Dexie at startup.
  // The in-memory syncStore.errorCount resets to 0 on every page load.
  // Reading it from Dexie immediately gives the user an accurate error
  // indicator before any sync cycle runs (e.g. on a cold restart with no
  // network, or while the first processQueue() is still in progress).
  syncManager.refreshErrorCount().catch((err) => {
    console.warn('[boot] Error count refresh failed:', err)
  })

  // Hydrate syncDisabled from AuthDB before the first processQueue().
  // getSyncEnabled() returns true by default (when no row exists).
  getSyncEnabled().then((enabled) => {
    syncStore.setSyncDisabled(!enabled)
  }).catch((err) => {
    console.warn('[boot] getSyncEnabled failed:', err)
  })

  // Check backend reachability at boot.
  // onOnline() only fires on transitions — if the device is already online,
  // no transition fires. This call handles the cold-start case.
  checkAndSetOnline().then((reachable) => {
    if (reachable && !syncStore.syncDisabled) syncManager.processQueue()
  }).catch((err) => {
    console.warn('[boot] Backend connectivity check failed:', err)
  })
})

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
 * Why call checkAndSetOnline() at boot?
 * The onOnline() watcher only fires on *transitions* (false → true). If the
 * device is already online when the app starts, no transition event fires and
 * the queue would never be processed until the next connectivity change. The
 * explicit boot-time health check handles the "user opens the app with WiFi
 * already active and has queued mutations from a previous offline session"
 * scenario, and also detects when the backend itself is down at launch time.
 *
 * Why not import syncManager from '@/offline' (the barrel)?
 * We import directly from '@/offline/sync-manager' to avoid a circular
 * dependency: index.ts re-exports everything including sync-manager, and
 * sync-manager imports from api/* which import from '@/types'. Using the
 * barrel here is fine too — kept as direct import for explicit clarity.
 *
 * Note: useNetworkStatus() calls useOnline() internally. VueUse ensures all
 * callers share the exact same underlying Ref<boolean> — there is only one
 * global listener.
 */
import { syncManager } from '@/offline/sync-manager'
import { useNetworkStatus } from '@/composables/useNetworkStatus'
import { checkBackendHealth } from '@/api/health'
import { useSyncStore } from '@/stores/sync'
import { useAccountsStore } from '@/stores/accounts'
import { useTransactionsStore } from '@/stores/transactions'
import { useTransfersStore } from '@/stores/transfers'
import { useCategoriesStore } from '@/stores/categories'
import { useDashboardsStore } from '@/stores/dashboards'

const { onOnline, onOffline } = useNetworkStatus()

/**
 * Phase 5 — Wire the sync store to network events.
 *
 * Why set it here and not inside the syncStore itself?
 * The syncStore is a plain Pinia store with no side effects. It does not know
 * about VueUse or navigator.onLine — it just holds state. main.ts is the
 * correct place to wire external signals (network + backend health) into the
 * store, just as it wires syncManager.processQueue() to network transitions.
 *
 * Why checkAndSetOnline() instead of syncStore.setOnline(isOnline.value)?
 * navigator.onLine only reflects device-level connectivity. The backend can
 * be down even when the device has internet. checkAndSetOnline() actively
 * probes the /health endpoint so syncStore.isOnline tracks backend
 * reachability, not just network presence.
 */
const syncStore = useSyncStore()

/**
 * Checks whether the backend is reachable and updates syncStore.isOnline.
 *
 * Why short-circuit on navigator.onLine === false?
 * If the device has no network at all, a health-check HTTP call would
 * fail immediately anyway. Skipping it avoids a 5-second timeout wait
 * and signals offline instantly.
 *
 * Why not use isOnline.value (VueUse) here?
 * After this change, isOnline.value still reflects navigator.onLine —
 * it is only used for the short-circuit guard. The source of truth for
 * "can we sync?" is syncStore.isOnline (backend-reachable), which this
 * function sets.
 */
async function checkAndSetOnline(): Promise<boolean> {
  if (!navigator.onLine) {
    syncStore.setOnline(false)
    return false
  }
  const reachable = await checkBackendHealth()
  syncStore.setOnline(reachable)
  return reachable
}


// On device regaining network — check backend and sync if reachable.
onOnline(() => {
  checkAndSetOnline().then((reachable) => {
    if (reachable && !syncStore.syncDisabled) syncManager.processQueue()
  }).catch((err) => {
    console.warn('[online] Backend connectivity check failed:', err)
  })
})

onOffline(() => {
  syncStore.setOnline(false)
})

// Trigger an immediate sync whenever a new mutation is enqueued while online.
// The SyncManager's `processing` flag prevents concurrent runs — extra calls
// while a sync is already in progress are silent no-ops.
window.addEventListener('wallet:mutation-queued', () => {
  // Guard on syncStore.isOnline (backend-reachable), not navigator.onLine.
  if (syncStore.isOnline && !syncStore.syncDisabled) {
    syncManager.processQueue()
  }
})

// Periodic connectivity check every 30 seconds.
// Handles backend-came-back-without-network-event and backend-went-down cases.
setInterval(() => {
  checkAndSetOnline().then((reachable) => {
    if (reachable && !syncStore.syncDisabled) syncManager.processQueue()
  }).catch((err) => {
    console.warn('[poll] Backend connectivity check failed:', err)
  })
}, 30_000)

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
