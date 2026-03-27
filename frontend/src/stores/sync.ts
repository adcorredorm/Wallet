/**
 * Sync Store — Phase 5
 *
 * Why a dedicated store for sync state?
 * The SyncManager (sync-manager.ts) is a background I/O singleton intentionally
 * kept free of Pinia imports. By contrast, this store is the reactive "window"
 * into that background process — it holds only UI-facing state that components
 * can subscribe to. This separation keeps the sync engine testable in isolation
 * while giving the UI a single reactive source of truth for connectivity and
 * sync progress.
 *
 * Why Composition API (not Options API)?
 * Consistent with every other store in this codebase. The Composition style
 * with defineStore + setup function gives us better TypeScript inference and
 * matches the pattern already established in accounts.ts, ui.ts, etc.
 *
 * State shape:
 * - isOnline:      mirrors navigator.onLine, updated by main.ts via setters
 * - isSyncing:     true while processQueue() is running
 * - pendingCount:  number of mutations waiting to be sent to the server
 * - errorCount:    number of mutations that failed permanently
 * - lastSyncAt:    ISO timestamp of the last completed processQueue() run
 * - errors:        array of SyncError objects for display in the UI
 *
 * The computed `syncStatus` collapses all of the above into a single token
 * that drives component styling (color, icon, label).
 */

import { defineStore } from 'pinia'
import { ref, computed, readonly } from 'vue'

export interface SyncError {
  entityType: string
  entityId: string
  operation: string
  message: string
  timestamp: string
}

export const useSyncStore = defineStore('sync', () => {
  // ── Reactive state ──────────────────────────────────────────────────────

  /**
   * Mirrors navigator.onLine. Updated by main.ts using the onOnline/onOffline
   * callbacks from useNetworkStatus() so it stays reactive to connectivity
   * changes without the store importing VueUse directly.
   */
  const isOnline = ref(navigator.onLine)

  /**
   * True while SyncManager.processQueue() is running.
   * Toggled by the sync-manager via setSyncing() so the UI can show a
   * spinning indicator during active sync.
   */
  const isSyncing = ref(false)

  /**
   * Number of mutations in the queue waiting to be sent to the server.
   * Updated at the start of every processQueue() call by reading
   * mutationQueue.count() in sync-manager.ts.
   */
  const pendingCount = ref(0)

  /**
   * Number of mutations that have failed permanently (HTTP 4xx or max
   * retries exceeded). Derived from the errors array length but also
   * settable directly so sync-manager.ts doesn't have to reconstruct the
   * errors array just to update the count.
   */
  const errorCount = ref(0)

  /**
   * ISO timestamp of the last time processQueue() completed successfully
   * (including the fullReadSync). null means the sync has never run in this
   * session. Used by useSyncStatus to show "Sincronizado hace X" style labels
   * (currently just "Sincronizado" for simplicity).
   */
  const lastSyncAt = ref<string | null>(null)

  /**
   * True once the first full read-sync has completed successfully.
   * Used by the SyncManager to gate incremental sync — incremental requests
   * only make sense after the initial dataset has been bootstrapped into
   * IndexedDB. Exposed as readonly so only setInitialSyncComplete() can
   * transition it from false → true; prevents accidental direct mutation
   * by components.
   */
  const initialSyncComplete = ref(false)

  /**
   * Detailed list of sync errors for potential display in a future error
   * detail sheet. Each entry carries enough context to identify which entity
   * failed and why.
   */
  const errors = ref<SyncError[]>([])

  /**
   * True when the user is online but not authenticated (guest mode).
   * When isGuest is true, the sync engine intentionally skips all network
   * operations — there is no user session to sync to.
   *
   * Why a separate flag instead of deriving from authStore.isAuthenticated?
   * sync.ts is intentionally free of Pinia store imports (see architectural
   * note at the top of this file). The SyncManager sets this flag by calling
   * setGuest() after checking auth state in its own init sequence, keeping
   * the sync store self-contained and testable without an auth dependency.
   */
  const isGuest = ref(false)

  /**
   * Controls the visibility of SyncErrorSheet.vue bottom sheet.
   * Toggled by SyncIndicator (open) and SyncErrorSheet itself (close).
   */
  const syncErrorSheetOpen = ref(false)

  /**
   * True when the user has explicitly disabled cloud sync via Settings.
   * When syncDisabled is true, SyncManager skips processQueue() and the UI
   * shows a fixed grey cloud. The mutation queue continues enqueuing locally.
   * Persisted in AuthDB — hydrated at boot from main.ts.
   */
  const syncDisabled = ref(false)

  // ── Computed: collapsed status token ────────────────────────────────────

  /**
   * Priority order (highest to lowest):
   * 1. offline  — device has no connectivity; nothing can sync
   * 2. guest    — online but not authenticated; sync is intentionally skipped
   * 3. syncing  — a sync is actively in progress
   * 4. error    — at least one mutation failed permanently
   * 5. pending  — mutations are queued but not yet sent
   * 6. synced   — everything is up to date
   *
   * Why check offline first?
   * If we are offline and also have errors, showing "error" would be
   * misleading — the user cannot fix connectivity-related issues by doing
   * anything in the app. "offline" is the more actionable and accurate state.
   *
   * Why does guest beat syncing/error/pending?
   * If the user is not authenticated, syncing/error/pending states are
   * irrelevant — the sync engine is not running at all in guest mode.
   * Showing "guest" makes it immediately clear why data is not syncing.
   */
  const syncStatus = computed<'disabled' | 'synced' | 'syncing' | 'pending' | 'error' | 'offline' | 'guest'>(() => {
    if (syncDisabled.value) return 'disabled'
    if (!isOnline.value) return 'offline'
    if (isGuest.value) return 'guest'
    if (isSyncing.value) return 'syncing'
    if (errorCount.value > 0) return 'error'
    if (pendingCount.value > 0) return 'pending'
    return 'synced'
  })

  // ── Setters (called by sync-manager.ts and main.ts) ─────────────────────

  function setOnline(value: boolean): void {
    isOnline.value = value
  }

  function setSyncing(value: boolean): void {
    isSyncing.value = value
  }

  function setPendingCount(count: number): void {
    pendingCount.value = count
  }

  function setErrorCount(count: number): void {
    errorCount.value = count
  }

  function setLastSyncAt(ts: string): void {
    lastSyncAt.value = ts
  }

  function setInitialSyncComplete(value: boolean): void {
    initialSyncComplete.value = value
  }

  /**
   * Set the guest mode flag. Called by the SyncManager after checking
   * authentication state: setGuest(true) when no user is authenticated,
   * setGuest(false) after a successful login/refresh.
   */
  function setGuest(value: boolean): void {
    isGuest.value = value
  }

  /**
   * Add a new sync error to the errors array and bump the errorCount.
   * Called by sync-manager.ts whenever a mutation fails permanently.
   */
  function addError(error: SyncError): void {
    errors.value.push(error)
    errorCount.value = errors.value.length
  }

  /**
   * Clear all recorded errors and reset errorCount to 0.
   * Intended for a future "dismiss errors" UI action.
   */
  function clearErrors(): void {
    errors.value = []
    errorCount.value = 0
  }

  function setSyncErrorSheetOpen(value: boolean): void {
    syncErrorSheetOpen.value = value
  }

  function setSyncDisabled(value: boolean): void {
    syncDisabled.value = value
  }

  return {
    // State
    isOnline,
    isSyncing,
    pendingCount,
    errorCount,
    lastSyncAt,
    initialSyncComplete: readonly(initialSyncComplete),
    isGuest,
    errors,
    syncErrorSheetOpen,
    syncDisabled,
    // Computed
    syncStatus,
    // Actions
    setOnline,
    setSyncing,
    setPendingCount,
    setErrorCount,
    setLastSyncAt,
    setInitialSyncComplete,
    setGuest,
    addError,
    clearErrors,
    setSyncErrorSheetOpen,
    setSyncDisabled,
  }
})
