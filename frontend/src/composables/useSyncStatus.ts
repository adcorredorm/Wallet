/**
 * useSyncStatus — composable that bridges the sync store to UI components
 *
 * Why a composable instead of using useSyncStore() directly in components?
 * Two reasons:
 *
 * 1. Derived presentation state lives here, not in the store.
 *    The store knows *what* the status is (an enum-like token). This
 *    composable knows *how to display it* (a Spanish label and a Tailwind
 *    color class). Keeping presentation logic out of the store makes the
 *    store more reusable and the composable independently testable.
 *
 * 2. Single import point for sync UI.
 *    A component only needs `import { useSyncStatus } from '@/composables/useSyncStatus'`
 *    to get both the raw store state (spread via `...syncStore`) and the
 *    derived display properties. No need to import both the store and a
 *    formatter utility separately.
 *
 * Why spread `...syncStore` at the return?
 * Re-exporting the store's refs directly (isOnline, isSyncing, etc.) means
 * components can destructure a single composable call and get everything they
 * need. The store refs remain reactive because we spread the reactive object,
 * not a snapshot.
 *
 * Why Tailwind color classes instead of CSS variables?
 * The project uses Tailwind utility classes throughout (see tailwind.config.js).
 * Returning class strings keeps styling consistent with the rest of the UI and
 * avoids introducing a parallel CSS variable system for a handful of colors.
 * The color tokens used here (amber-400, blue-400, red-400, green-400,
 * slate-400) are standard Tailwind — no custom config needed.
 */

import { computed } from 'vue'
import { useSyncStore } from '@/stores/sync'

export function useSyncStatus() {
  const syncStore = useSyncStore()

  /**
   * Human-readable Spanish label for the current sync state.
   *
   * Why Spanish?
   * The entire application UI is in Spanish (see AppNavigation.vue labels,
   * EmptyState messages, etc.). Sync status labels follow the same convention.
   *
   * Why pluralise pendingCount and errorCount?
   * "1 pendiente" vs "2 pendientes" — correct Spanish plural form improves
   * perceived quality on mobile where the indicator is small and every
   * character counts.
   */
  const statusLabel = computed(() => {
    switch (syncStore.syncStatus) {
      case 'offline':
        return 'Sin conexión'
      case 'guest':
        // Why "Modo invitado" and not "No autenticado"?
        // "Modo invitado" is friendly and describes the UX state the user is
        // in, rather than a technical condition. It matches the language used
        // in the GuestBanner component ("Los cambios no se sincronizarán").
        return 'Modo invitado'
      case 'syncing':
        return 'Sincronizando...'
      case 'pending':
        return `${syncStore.pendingCount} pendiente${syncStore.pendingCount !== 1 ? 's' : ''}`
      case 'error':
        return `${syncStore.errorCount} error${syncStore.errorCount !== 1 ? 'es' : ''}`
      case 'synced':
        return syncStore.lastSyncAt ? 'Sincronizado' : 'Listo'
    }
  })

  /**
   * Tailwind text color class for the current sync state.
   *
   * Color decisions:
   * - offline → amber-400  (warning; not an error, just a connectivity state)
   * - syncing → blue-400   (accent-blue from tailwind.config.js — active/in-progress)
   * - pending → amber-400  (same as offline — waiting, not failed)
   * - error   → red-400    (accent-red — something went wrong, needs attention)
   * - synced  → green-400  (accent-green — all good)
   *
   * Why 400 variants instead of 500?
   * The dark background (#0f172a, #1e293b) makes 500 variants look too
   * saturated. The 400 shade provides good contrast (>= 4.5:1 against the
   * dark background) while feeling softer, which is appropriate for a
   * secondary indicator that should not compete with primary content.
   */
  const statusColor = computed(() => {
    switch (syncStore.syncStatus) {
      case 'offline':  return 'text-amber-400'
      // guest uses amber: same "attention" tone as offline — data is safe
      // locally but is not syncing. Not an error, just a notable state.
      case 'guest':    return 'text-amber-400'
      case 'syncing':  return 'text-blue-400'
      case 'pending':  return 'text-amber-400'
      case 'error':    return 'text-red-400'
      case 'synced':   return 'text-green-400'
    }
  })

  return {
    // Spread store refs so consumers can destructure them directly.
    // These remain reactive because useSyncStore() returns a reactive proxy.
    ...syncStore,
    // Derived display properties
    statusLabel,
    statusColor
  }
}
