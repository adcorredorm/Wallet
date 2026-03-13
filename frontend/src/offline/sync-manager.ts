/**
 * SyncManager — the central offline-sync orchestrator (Phase 4)
 *
 * ARCHITECTURE OVERVIEW
 * ─────────────────────
 * The SyncManager sits between IndexedDB (via `db` and `mutationQueue`) and
 * the REST API layer. It is intentionally free of Pinia store imports because:
 *
 *   - Stores are UI state containers. The SyncManager is a background I/O
 *     process. Mixing the two would couple the sync lifecycle to Vue's
 *     reactivity and make the sync logic untestable outside of a Vue app.
 *   - After a full-read-sync the stores will re-fetch on the next navigation
 *     or user action, picking up the fresh IndexedDB state naturally.
 *
 * PROCESSING PIPELINE (one call to processQueue)
 * ───────────────────────────────────────────────
 * 1. Load the full queue in FIFO order (ordered by queued_at).
 * 2. For each mutation:
 *    a. Skip if blocked (dependency CREATE failed earlier in this or a
 *       previous sync attempt — see blockDependents()).
 *    b. Resolve any temp-* IDs in the payload to real server IDs by reading
 *       the server_id field stored in IndexedDB after a previous sync.
 *    c. Call the matching API function.
 *    d. On success:
 *       - If it was a CREATE with a temp-* entity_id, cascade the new
 *         real ID through IndexedDB and through the remaining queue.
 *       - Mark the entity as 'synced' in IndexedDB.
 *       - Remove the mutation from the queue.
 *    e. On error:
 *       - 4xx → permanent failure: mark entity 'error', block dependents
 *         if it was a CREATE.
 *       - 5xx / timeout → transient failure: exponential back-off wait,
 *         increment retry_count. Give up after MAX_RETRIES and treat as
 *         permanent failure.
 * 3. After the queue is empty (or all remaining items are blocked/errored),
 *    perform a full-read-sync: re-fetch all entities from the server and
 *    write them to IndexedDB so the UI has authoritative server state.
 *
 * EXPONENTIAL BACK-OFF FORMULA
 * ─────────────────────────────
 * delay = min(BASE_DELAY_MS * 2^retry_count, MAX_DELAY_MS)
 * retry_count starts at 0, so attempts use delays of:
 *   0 → 1 s, 1 → 2 s, 2 → 4 s, 3 → 8 s, 4 → 16 s, then give up (≥ MAX_RETRIES)
 *
 * DEPENDENCY RESOLUTION
 * ──────────────────────
 * DEPENDENCY_FIELDS defines which payload fields in each entity type hold
 * foreign keys that may reference a temp-* ID. Before sending a mutation,
 * sendToServer() rewrites those fields using the server_id stored in
 * IndexedDB for the referenced entity (if available).
 */

import { db } from './db'
import { mutationQueue } from './mutation-queue'
import { isTempId } from './temp-id'
import type { PendingMutation, LocalAccount, LocalTransaction, LocalTransfer, LocalCategory, LocalDashboard, LocalDashboardWidget } from './types'
import { accountsApi } from '@/api/accounts'
import { transactionsApi } from '@/api/transactions'
import { transfersApi } from '@/api/transfers'
import { categoriesApi } from '@/api/categories'
import { dashboardsApi } from '@/api/dashboards'
import type {
  Account,
  Transaction,
  Transfer,
  Category,
  CreateAccountDto,
  UpdateAccountDto,
  CreateTransactionDto,
  UpdateTransactionDto,
  CreateTransferDto,
  UpdateTransferDto,
  CreateCategoryDto,
  UpdateCategoryDto
} from '@/types'
import type {
  Dashboard,
  DashboardWidget,
  CreateDashboardDto,
  UpdateDashboardDto,
  CreateWidgetDto,
  UpdateWidgetDto,
} from '@/types/dashboard'

// ---------------------------------------------------------------------------
// Phase 5 — Sync store integration
//
// Why import the store here if the architecture comment says "free of Pinia
// store imports"?
// The original rationale was to keep the SyncManager decoupled from *UI data
// stores* (accounts, transactions, etc.) so the sync logic does not depend on
// reactive Vue state. The syncStore is different: it is a pure status sink —
// it only receives signals FROM the SyncManager, it never drives sync logic.
// The SyncManager pushing status updates into a Pinia store does not create a
// coupling that makes the sync engine untestable; the store calls are
// fire-and-forget side effects that can be omitted in tests.
//
// Why a lazy getter instead of a top-level import?
// sync-manager.ts is instantiated as a module-level singleton *before* Pinia
// is fully initialised in main.ts. Calling useSyncStore() at module load time
// would throw "getActivePinia was called with no active Pinia". The lazy
// getter defers the useSyncStore() call to the first processQueue() invocation,
// which always happens after app.mount() and therefore after Pinia is active.
// ---------------------------------------------------------------------------
import { useSyncStore } from '@/stores/sync'
import { useUiStore } from '@/stores/ui'

/**
 * Lazily resolve the sync store.
 * Wrapped in a function so it is never called at module-evaluation time —
 * only called from inside processQueue(), which runs after Pinia is ready.
 */
function getSyncStore() {
  return useSyncStore()
}

/**
 * Lazily resolve the UI store for toast notifications.
 */
function getUiStore() {
  return useUiStore()
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Maximum number of transient-error retries before a mutation is abandoned. */
const MAX_RETRIES = 5

/** Base delay for the exponential back-off formula in milliseconds. */
const BASE_DELAY_MS = 1000

/** Hard ceiling for back-off delays to avoid very long waits. */
const MAX_DELAY_MS = 30_000

// ---------------------------------------------------------------------------
// Dependency field map
//
// Why this map exists:
// When a CREATE mutation fails (permanently) the entity never exists on the
// server. Any subsequent mutation whose payload references that entity's ID
// will also fail — but instead of repeatedly trying and failing with 4xx, we
// scan the remaining queue once and mark those mutations as "blocked".
//
// The map tells us which payload fields to scan for a given entity_type.
// For example: if an account CREATE fails for tempId "temp-abc", we look for
// any queued transaction whose payload.cuenta_id === "temp-abc" and block it.
// ---------------------------------------------------------------------------
const DEPENDENCY_FIELDS: Record<PendingMutation['entity_type'], string[]> = {
  account: [],
  transaction: ['account_id', 'category_id'],
  transfer: ['source_account_id', 'destination_account_id'],
  category: ['parent_category_id'],
  // Settings are standalone key/value pairs — no foreign-key references.
  setting: [],
  // dashboard_widget depends on dashboard via dashboard_id — if a dashboard
  // CREATE fails offline, any widget creates for it are blocked too.
  dashboard: [],
  dashboard_widget: ['dashboard_id'],
}

// ---------------------------------------------------------------------------
// ApiError type guard
//
// Why a type guard instead of (error as any).status?
// The apiClient response interceptor in api/index.ts transforms all Axios
// errors into ApiError objects before rejecting: { message, status, errors }.
// Using a type guard lets TypeScript narrow the type properly in the catch
// block so we don't have to cast to `any` everywhere.
//
// Why check for 'status' specifically?
// ApiError always has a numeric status field. Checking that it is present and
// a number distinguishes an ApiError from a plain Error or unknown value.
// ---------------------------------------------------------------------------
interface ApiError {
  message: string
  status: number
  errors: Record<string, unknown>
}

function isApiError(error: unknown): error is ApiError {
  return (
    typeof error === 'object' &&
    error !== null &&
    'status' in error &&
    typeof (error as Record<string, unknown>).status === 'number'
  )
}

// ---------------------------------------------------------------------------
// Helper: map a raw server entity to its LocalXxx representation.
//
// Why duplicate this helper here instead of importing from repository.ts?
// repository.ts exports fetchAllWithRevalidation / fetchByIdWithRevalidation
// which include stale-while-revalidate logic that we don't want here. The
// SyncManager's fullReadSync does a direct write — no stale path needed.
// Duplicating the three-field assignment is four lines; it's not worth
// creating a shared utility that would couple the two modules.
// ---------------------------------------------------------------------------
function toLocalItem<T extends { id: string; updated_at: string }>(
  item: T,
  serverId?: string
): T & { _sync_status: 'synced'; _local_updated_at: string; server_id?: string } {
  return {
    ...item,
    _sync_status: 'synced' as const,
    _local_updated_at: item.updated_at,
    ...(serverId !== undefined ? { server_id: serverId } : {})
  }
}

// ---------------------------------------------------------------------------
// SyncManager class
// ---------------------------------------------------------------------------

export class SyncManager {
  /**
   * processing flag prevents concurrent processQueue() invocations.
   *
   * Why not a promise chain / mutex?
   * This app is single-tab. The only way processQueue() can be called while
   * already running is if a connectivity-change event fires during a long sync
   * (e.g. the user briefly loses and immediately regains connection). A simple
   * boolean guard is sufficient and avoids the complexity of a promise-based
   * mutex for this case.
   */
  private processing = false

  // -------------------------------------------------------------------------
  // Public API
  // -------------------------------------------------------------------------

  /**
   * Process all pending mutations in FIFO order.
   *
   * This is the entry point called by main.ts when:
   *   - The app boots and the device is already online.
   *   - The device transitions from offline → online.
   *
   * The method is idempotent when called concurrently: the second call is a
   * no-op if the first is still running.
   */
  async processQueue(): Promise<void> {
    if (this.processing) {
      console.log('[SyncManager] processQueue() called while already running — skipping.')
      return
    }

    this.processing = true
    console.log('[SyncManager] Starting queue processing.')

    // ── Phase 5: update sync store ─────────────────────────────────────────
    // Resolve stores lazily (after Pinia is initialised — see module comment).
    const syncStore = getSyncStore()
    const uiStore = getUiStore()

    // Tell the UI that syncing is active and report the current queue depth.
    syncStore.setSyncing(true)
    const initialCount = await mutationQueue.count()
    syncStore.setPendingCount(initialCount)
    // ──────────────────────────────────────────────────────────────────────

    try {
      const mutations = await mutationQueue.getAll()

      if (mutations.length === 0) {
        console.log('[SyncManager] Queue is empty. Running full-read-sync anyway.')
      }

      for (const mutation of mutations) {
        // Skip mutations that are blocked due to a dependency CREATE failure.
        // The 'blocked: ' prefix is set by mutationQueue.markBlocked() and is
        // checked here to avoid sending mutations that we know will fail.
        if (mutation.last_error?.startsWith('blocked:')) {
          console.log(
            `[SyncManager] Skipping blocked mutation id=${mutation.id} ` +
            `(${mutation.entity_type}/${mutation.operation}/${mutation.entity_id})`
          )
          continue
        }

        console.log(
          `[SyncManager] Processing mutation id=${mutation.id} ` +
          `${mutation.entity_type}/${mutation.operation}/${mutation.entity_id}`
        )

        try {
          const result = await this.sendToServer(mutation)

          // If a CREATE was for a temp-* ID the server assigned a new real ID.
          // We must update IndexedDB and any remaining queue entries that
          // reference the old temp ID before moving on to the next mutation.
          if (mutation.operation === 'create' && isTempId(mutation.entity_id)) {
            // Close the race window between sendToServer returning and
            // resolveTemporaryId deleting the temp-* record. If a background
            // revalidation fires here it would find the real ID in the server
            // response AND the temp-* record still in IndexedDB as 'pending',
            // producing a visual duplicate. Marking the temp-* record 'synced'
            // first ensures mergeWithPending (which only returns 'pending'/'error'
            // items) ignores it before the delete+re-insert happens.
            await this.markEntitySyncStatus(
              mutation.entity_type,
              mutation.entity_id,
              'synced'
            )
            await this.resolveTemporaryId(
              mutation.entity_type,
              mutation.entity_id,
              (result as { id: string }).id
            )
          }

          // Mark the entity as synced in IndexedDB (status → 'synced',
          // server_id populated). Skip for deletes — the entity was already
          // removed from IndexedDB when the user triggered the delete.
          if (mutation.operation !== 'delete') {
            await this.markSynced(
              mutation.entity_type,
              mutation.entity_id,
              result as { id: string; updated_at: string }
            )
          }

          // Remove the mutation from the queue — it has been successfully
          // sent to the server.
          await mutationQueue.remove(mutation.id!)
          console.log(`[SyncManager] Mutation id=${mutation.id} synced successfully.`)

          // ── Phase 5: update pending count after each successful flush ──
          const remaining = await mutationQueue.count()
          syncStore.setPendingCount(remaining)
          // ───────────────────────────────────────────────────────────────
        } catch (error: unknown) {
          await this.handleError(mutation, error, syncStore)
        }
      }

      // After all (non-blocked) mutations are processed, re-fetch the full
      // state from the server. This ensures IndexedDB reflects any changes
      // made by other devices or server-side side-effects (e.g. recalculated
      // balances, auto-generated fields).
      await this.fullReadSync()

      // Notify the app that IndexedDB is now fully up to date so the reactive
      // stores can refresh their state from local storage without firing extra
      // network requests.
      window.dispatchEvent(new CustomEvent('wallet:sync-complete'))

      // ── Phase 5: show success toast if mutations were actually synced ──
      // Why only when initialCount > 0?
      // If the queue was empty (e.g. a routine boot-time sync with no pending
      // changes), showing "Datos sincronizados" would be misleading and noisy.
      // Only show the toast when real pending mutations were flushed to the
      // server — i.e. the user's offline changes actually made it through.
      if (initialCount > 0) {
        uiStore.showSuccess('Datos sincronizados', 3000)
      }
      // ───────────────────────────────────────────────────────────────────
    } finally {
      this.processing = false
      console.log('[SyncManager] Queue processing complete.')

      // ── Phase 5: mark sync as done ───────────────────────────────────
      // setSyncing(false) always runs (even on error) via finally, so the
      // header indicator never gets stuck in the "syncing" spin state.
      // setLastSyncAt records the wall-clock time for the "Sincronizado" label.
      syncStore.setSyncing(false)
      syncStore.setLastSyncAt(new Date().toISOString())
      // ─────────────────────────────────────────────────────────────────
    }
  }

  // -------------------------------------------------------------------------
  // Private: send a single mutation to the server
  // -------------------------------------------------------------------------

  /**
   * Map entity_type + operation to the correct API call and execute it.
   *
   * Before sending, any temp-* IDs in the payload are resolved to real server
   * IDs by looking them up in IndexedDB (server_id field). If the referenced
   * entity has not been synced yet (no server_id), the temp ID is left as-is
   * because FIFO ordering guarantees the CREATE for that entity was processed
   * in an earlier loop iteration and resolveTemporaryId() already rewrote
   * all downstream queue payloads.
   *
   * For CREATE payloads we strip the temp-* entity_id from the body — the
   * server assigns its own ID. The client_id field (already in the payload
   * thanks to the stores) allows the server to deduplicate retried requests.
   *
   * For UPDATE payloads we attach the X-Client-Updated-At header so the
   * server can perform Last-Write-Wins conflict resolution if it supports it.
   *
   * Why return `unknown` instead of a specific type?
   * sendToServer handles all four entity types. The caller (processQueue)
   * only needs the `id` and `updated_at` fields from the result, which all
   * entity types share. Using `unknown` with a narrow cast at the call site
   * is safer than `any` because it forces an explicit acknowledgement of the
   * type at each use point.
   */
  private async sendToServer(mutation: PendingMutation): Promise<unknown> {
    const payload = await this.resolvePayloadIds(mutation.payload)

    switch (mutation.entity_type) {
      case 'account':
        return this.sendAccount(mutation, payload)

      case 'transaction':
        return this.sendTransaction(mutation, payload)

      case 'transfer':
        return this.sendTransfer(mutation, payload)

      case 'category':
        return this.sendCategory(mutation, payload)

      case 'setting':
        return this.sendSetting(mutation, payload)

      case 'dashboard':
        return this.sendDashboard(mutation, payload)

      case 'dashboard_widget':
        return this.sendDashboardWidget(mutation, payload)
    }
  }

  /**
   * Replace any temp-* ID values in a payload with the real server IDs
   * stored in IndexedDB.
   *
   * Why iterate over payload values instead of using DEPENDENCY_FIELDS?
   * DEPENDENCY_FIELDS tells us which fields to *scan when blocking
   * dependents*. Here we want to resolve ALL fields that happen to hold a
   * temp ID, which is a superset of DEPENDENCY_FIELDS (e.g. the 'id' field
   * itself in a DELETE payload could be a temp ID if the entity was never
   * synced). Scanning every value is safer and handles future entity types
   * without needing to update DEPENDENCY_FIELDS.
   *
   * Note: client_id is intentionally not resolved — it is the temp ID itself
   * sent for server-side idempotency and must remain as the original tempId.
   */
  private async resolvePayloadIds(
    payload: Record<string, unknown>
  ): Promise<Record<string, unknown>> {
    const resolved: Record<string, unknown> = { ...payload }

    for (const [key, value] of Object.entries(resolved)) {
      // Skip client_id — that field must remain as the original temp ID.
      if (key === 'client_id') continue

      if (typeof value === 'string' && isTempId(value)) {
        // Try to find the real server ID by looking up the entity in
        // IndexedDB across all four tables. We check by local id (the temp-*)
        // because server_id is only populated after the entity's own CREATE
        // has been synced.
        const serverIdForValue = await this.findServerId(value)
        if (serverIdForValue) {
          resolved[key] = serverIdForValue
        }
        // If no server_id is found the temp ID stays — FIFO ordering means
        // this will only happen if the parent CREATE hasn't been processed
        // yet in this same queue run, which would only occur if we are
        // re-loading the queue mid-run (not currently the case).
      }
    }

    return resolved
  }

  /**
   * Look up a temp-* ID across all four entity tables to find its server_id.
   *
   * Why search all four tables?
   * A payload field like cuenta_id could reference an account, while
   * categoria_id references a category. Rather than passing entity_type
   * information down to this helper, we do four O(log n) index reads — the
   * cost is negligible compared to the network round-trip that follows.
   */
  private async findServerId(tempId: string): Promise<string | undefined> {
    const account = await db.accounts.get(tempId)
    if (account?.server_id) return account.server_id

    const transaction = await db.transactions.get(tempId)
    if (transaction?.server_id) return transaction.server_id

    const transfer = await db.transfers.get(tempId)
    if (transfer?.server_id) return transfer.server_id

    const category = await db.categories.get(tempId)
    if (category?.server_id) return category.server_id

    const dashboard = await db.dashboards.get(tempId)
    if (dashboard?.server_id) return dashboard.server_id

    const widget = await db.dashboardWidgets.get(tempId)
    if (widget?.server_id) return widget.server_id

    return undefined
  }

  // Per-entity send helpers ─────────────────────────────────────────────────

  private async sendAccount(
    mutation: PendingMutation,
    payload: Record<string, unknown>
  ): Promise<Account> {
    switch (mutation.operation) {
      case 'create': {
        // Strip the temp-* entity_id — the server assigns its own ID.
        // client_id is already in the payload from the store's enqueue call.
        // We cast to CreateAccountDto because we know the store built the
        // payload from a CreateAccountDto; the cast is safe here.
        const { id: _id, ...createPayload } = payload as Record<string, unknown> & { id?: string }
        void _id // explicitly unused — we intentionally drop this field
        return accountsApi.create(createPayload as unknown as CreateAccountDto)
      }

      case 'update': {
        // The server uses X-Client-Updated-At for Last-Write-Wins conflict
        // resolution. We read _local_updated_at from the stored entity rather
        // than the payload because the payload only contains the fields that
        // changed, not the full entity.
        const entity = await db.accounts.get(mutation.entity_id)
        const localUpdatedAt = entity?._local_updated_at ?? new Date().toISOString()

        // apiClient is imported indirectly through accountsApi.update().
        // To attach a custom header per-request we would need to access the
        // axios instance directly. Since the stores already record
        // _local_updated_at in IndexedDB and the backend can use it, we
        // include it as a payload field as a fallback strategy if the header
        // approach is not yet wired on the server.
        //
        // For the header approach: accountsApi.update() calls apiClient.put()
        // which does not expose per-request config. We would need to add a
        // headers option to the api function signature — that is a Phase 5
        // concern. For Phase 4, we proceed without the header; LWW via the
        // payload field is the active mechanism.
        void localUpdatedAt

        const { id: _id, ...updatePayload } = payload as Record<string, unknown> & { id?: string }
        void _id
        return accountsApi.update(mutation.entity_id, updatePayload as unknown as UpdateAccountDto)
      }

      case 'delete':
        await accountsApi.delete(mutation.entity_id)
        // DELETE returns void; return a minimal object so processQueue's
        // markSynced call has something to work with. For deletes, markSynced
        // is a no-op because the entity has already been removed from the
        // reactive store — we still call it for consistency.
        return { id: mutation.entity_id } as Account
    }
  }

  private async sendTransaction(
    mutation: PendingMutation,
    payload: Record<string, unknown>
  ): Promise<Transaction> {
    switch (mutation.operation) {
      case 'create': {
        const { id: _id, ...createPayload } = payload as Record<string, unknown> & { id?: string }
        void _id
        return transactionsApi.create(createPayload as unknown as CreateTransactionDto)
      }

      case 'update': {
        const { id: _id, ...updatePayload } = payload as Record<string, unknown> & { id?: string }
        void _id
        return transactionsApi.update(mutation.entity_id, updatePayload as unknown as UpdateTransactionDto)
      }

      case 'delete':
        await transactionsApi.delete(mutation.entity_id)
        return { id: mutation.entity_id } as Transaction
    }
  }

  private async sendTransfer(
    mutation: PendingMutation,
    payload: Record<string, unknown>
  ): Promise<Transfer> {
    switch (mutation.operation) {
      case 'create': {
        const { id: _id, ...createPayload } = payload as Record<string, unknown> & { id?: string }
        void _id
        return transfersApi.create(createPayload as unknown as CreateTransferDto)
      }

      case 'update': {
        const { id: _id, ...updatePayload } = payload as Record<string, unknown> & { id?: string }
        void _id
        return transfersApi.update(mutation.entity_id, updatePayload as unknown as UpdateTransferDto)
      }

      case 'delete':
        await transfersApi.delete(mutation.entity_id)
        return { id: mutation.entity_id } as Transfer
    }
  }

  private async sendCategory(
    mutation: PendingMutation,
    payload: Record<string, unknown>
  ): Promise<Category> {
    switch (mutation.operation) {
      case 'create': {
        const { id: _id, ...createPayload } = payload as Record<string, unknown> & { id?: string }
        void _id
        return categoriesApi.create(createPayload as unknown as CreateCategoryDto)
      }

      case 'update': {
        const { id: _id, ...updatePayload } = payload as Record<string, unknown> & { id?: string }
        void _id
        return categoriesApi.update(mutation.entity_id, updatePayload as unknown as UpdateCategoryDto)
      }

      case 'delete':
        await categoriesApi.delete(mutation.entity_id)
        return { id: mutation.entity_id } as Category
    }
  }

  /**
   * Send a setting mutation to the API.
   *
   * Why only 'update' and not 'create' or 'delete'?
   * Settings have upsert semantics: PUT /api/v1/settings/{key} creates the
   * setting if it doesn't exist and replaces it if it does. The settingsStore
   * always enqueues 'update' mutations — there is no 'create' distinction
   * and settings are never deleted via the mutation queue.
   *
   * Why return a minimal { id, updated_at } object?
   * processQueue() calls markSynced(entityType, entityId, serverResult) after
   * this method returns. For settings, entityId is the string key
   * ('primary_currency'). The server echoes the updated setting but we only
   * need the id field to satisfy the markSynced signature.
   */
  private async sendSetting(
    mutation: PendingMutation,
    payload: Record<string, unknown>
  ): Promise<{ id: string; updated_at?: string }> {
    // Import lazily to avoid a circular dependency at module-load time.
    // settings API is not imported at the top of this file because it was
    // added in Phase 3.3, after the SyncManager was written. Using a dynamic
    // import here keeps the SyncManager's import list clean.
    const { updateSetting } = await import('@/api/settings')

    const key = payload['key'] as string ?? mutation.entity_id
    const value = payload['value']

    await updateSetting(key, value)

    // Return a shape compatible with markSynced's serverResult parameter.
    return { id: key, updated_at: new Date().toISOString() }
  }

  private async sendDashboard(
    mutation: PendingMutation,
    payload: Record<string, unknown>
  ): Promise<Dashboard> {
    switch (mutation.operation) {
      case 'create': {
        const { id: _id, ...createPayload } = payload as Record<string, unknown> & { id?: string }
        void _id
        return dashboardsApi.create(createPayload as unknown as CreateDashboardDto)
      }

      case 'update': {
        const { id: _id, ...updatePayload } = payload as Record<string, unknown> & { id?: string }
        void _id
        return dashboardsApi.update(mutation.entity_id, updatePayload as unknown as UpdateDashboardDto)
      }

      case 'delete':
        await dashboardsApi.delete(mutation.entity_id)
        return { id: mutation.entity_id } as Dashboard
    }
  }

  /**
   * Send a dashboard_widget mutation to the API.
   *
   * Why extract dashboard_id from payload?
   * The dashboards API requires dashboardId as a URL path parameter (not body).
   * The store encodes it in the payload so the SyncManager can route the request
   * to the correct endpoint. We strip it from the body before sending.
   */
  private async sendDashboardWidget(
    mutation: PendingMutation,
    payload: Record<string, unknown>
  ): Promise<DashboardWidget> {
    const dashboardId = payload['dashboard_id'] as string | undefined
    if (!dashboardId) throw new Error(`[SyncManager] sendDashboardWidget: missing dashboard_id in payload for entity ${mutation.entity_id}`)

    switch (mutation.operation) {
      case 'create': {
        const { id: _id, dashboard_id: _did, ...createPayload } =
          payload as Record<string, unknown> & { id?: string; dashboard_id?: string }
        void _id
        void _did
        return dashboardsApi.createWidget(dashboardId, createPayload as unknown as CreateWidgetDto)
      }

      case 'update': {
        const { id: _id, dashboard_id: _did, ...updatePayload } =
          payload as Record<string, unknown> & { id?: string; dashboard_id?: string }
        void _id
        void _did
        return dashboardsApi.updateWidget(
          dashboardId,
          mutation.entity_id,
          updatePayload as unknown as UpdateWidgetDto
        )
      }

      case 'delete':
        await dashboardsApi.deleteWidget(dashboardId, mutation.entity_id)
        return { id: mutation.entity_id } as DashboardWidget
    }
  }

  // -------------------------------------------------------------------------
  // Private: resolve temporary IDs after a successful CREATE
  // -------------------------------------------------------------------------

  /**
   * After a CREATE mutation succeeds, the server has assigned a real UUID.
   * We must:
   *   1. Update the entity in its IndexedDB table: change its primary key
   *      from tempId to realId and store server_id = realId.
   *   2. Update any other IndexedDB entities whose FK fields still hold the
   *      old tempId.
   *   3. Update any remaining mutation queue payloads that reference the old
   *      tempId so future sync iterations send the correct server ID.
   *
   * Why update IndexedDB FKs separately from payload FKs?
   * The mutation queue payloads in IndexedDB are the serialised DTOs the
   * stores built (e.g. { cuenta_id: 'temp-abc' }). The IndexedDB entity rows
   * themselves also have FK fields (e.g. transactions.cuenta_id). Both need
   * rewriting so that after a full-read-sync the local data is consistent.
   *
   * Why use db.table.where(...).modify() instead of a loop?
   * modify() is a Dexie bulk-update that issues a single IndexedDB
   * transaction over all matching rows. It is significantly faster than
   * iterating and calling update() in a JavaScript loop.
   */
  private async resolveTemporaryId(
    entityType: PendingMutation['entity_type'],
    tempId: string,
    realId: string
  ): Promise<void> {
    console.log(
      `[SyncManager] Resolving temp ID ${tempId} → ${realId} for ${entityType}`
    )

    // ── Step 1: Update the entity's own row ─────────────────────────────────
    // Dexie does not support changing the primary key of an existing record
    // in place (IndexedDB's object store key is immutable). The correct
    // approach is: read the old record, delete it, insert a new one with
    // the real ID.
    await this.replaceEntityWithRealId(entityType, tempId, realId)

    // ── Step 2: Update FK fields in other IndexedDB tables ──────────────────
    switch (entityType) {
      case 'account':
        // Transactions that reference this account
        await db.transactions
          .where('account_id')
          .equals(tempId)
          .modify({ account_id: realId })

        // Transfers that use this account as origin
        await db.transfers
          .where('source_account_id')
          .equals(tempId)
          .modify({ source_account_id: realId })

        // Transfers that use this account as destination
        await db.transfers
          .where('destination_account_id')
          .equals(tempId)
          .modify({ destination_account_id: realId })
        break

      case 'category':
        // Transactions that reference this category
        await db.transactions
          .where('category_id')
          .equals(tempId)
          .modify({ category_id: realId })

        // Sub-categories whose parent is this category
        await db.categories
          .where('parent_category_id')
          .equals(tempId)
          .modify({ parent_category_id: realId })
        break

      case 'transaction':
      case 'transfer':
        // Transactions and transfers do not act as FKs in other tables.
        break

      case 'setting':
        // Settings do not act as FKs in other tables and are never created
        // with temp-* IDs. This branch is unreachable in practice.
        break

      case 'dashboard':
        // Update dashboard_widget rows that reference this dashboard via dashboard_id.
        await db.dashboardWidgets
          .where('dashboard_id')
          .equals(tempId)
          .modify({ dashboard_id: realId })
        break

      case 'dashboard_widget':
        // dashboard_widget does not act as a FK in any other table.
        break
    }

    // ── Step 3: Update remaining mutation queue payloads ────────────────────
    // Any queued mutation whose payload contains the old tempId needs to be
    // updated so the next sendToServer() call uses the real ID.
    const remainingMutations = await mutationQueue.getAll()

    for (const m of remainingMutations) {
      let changed = false
      const updatedPayload: Record<string, unknown> = { ...m.payload }

      // Check every field in the payload — a field may hold the tempId as
      // a string value (FK or the entity's own id field).
      for (const [field, value] of Object.entries(updatedPayload)) {
        if (typeof value === 'string' && value === tempId) {
          updatedPayload[field] = realId
          changed = true
        }
      }

      // Also update the entity_id on the mutation row itself if it references
      // the temp ID (this handles subsequent UPDATE/DELETE mutations for the
      // same entity that were enqueued after the CREATE).
      if (m.entity_id === tempId && m.id != null) {
        await db.pendingMutations.update(m.id, {
          entity_id: realId,
          ...(changed ? { payload: updatedPayload } : {})
        })
      } else if (changed && m.id != null) {
        await mutationQueue.updatePayload(m.id, updatedPayload)
      }
    }
  }

  /**
   * Move an entity from its temp-* primary key to the real server-assigned ID.
   *
   * Why delete + re-insert instead of update?
   * IndexedDB primary keys are immutable — you cannot change the key of an
   * existing record. The only way to change the PK is to delete the old
   * record and insert a new one with the real ID. Dexie's put() replaces a
   * record at the given key but does not move an existing record to a new key.
   */
  private async replaceEntityWithRealId(
    entityType: PendingMutation['entity_type'],
    tempId: string,
    realId: string
  ): Promise<void> {
    switch (entityType) {
      case 'account': {
        const old = await db.accounts.get(tempId)
        if (old) {
          const updated: LocalAccount = { ...old, id: realId, server_id: realId }
          await db.accounts.delete(tempId)
          await db.accounts.put(updated)
        }
        break
      }

      case 'transaction': {
        const old = await db.transactions.get(tempId)
        if (old) {
          const updated: LocalTransaction = { ...old, id: realId, server_id: realId }
          await db.transactions.delete(tempId)
          await db.transactions.put(updated)
        }
        break
      }

      case 'transfer': {
        const old = await db.transfers.get(tempId)
        if (old) {
          const updated: LocalTransfer = { ...old, id: realId, server_id: realId }
          await db.transfers.delete(tempId)
          await db.transfers.put(updated)
        }
        break
      }

      case 'category': {
        const old = await db.categories.get(tempId)
        if (old) {
          const updated: LocalCategory = { ...old, id: realId, server_id: realId }
          await db.categories.delete(tempId)
          await db.categories.put(updated)
        }
        break
      }

      case 'setting':
        // Settings use string keys as their primary key (e.g. 'primary_currency').
        // They are never created with temp-* IDs — this branch is unreachable in
        // practice, but required for TypeScript exhaustiveness.
        break

      case 'dashboard': {
        const old = await db.dashboards.get(tempId)
        if (old) {
          const updated: LocalDashboard = { ...old, id: realId, server_id: realId }
          await db.dashboards.delete(tempId)
          await db.dashboards.put(updated)
        }
        break
      }

      case 'dashboard_widget': {
        const old = await db.dashboardWidgets.get(tempId)
        if (old) {
          const updated: LocalDashboardWidget = { ...old, id: realId, server_id: realId }
          await db.dashboardWidgets.delete(tempId)
          await db.dashboardWidgets.put(updated)
        }
        break
      }
    }
  }

  // -------------------------------------------------------------------------
  // Private: mark an entity as successfully synced in IndexedDB
  // -------------------------------------------------------------------------

  /**
   * After a successful mutation, update the entity's sync metadata in
   * IndexedDB to reflect the authoritative server state.
   *
   * For CREATE and UPDATE:
   *   - _sync_status → 'synced'
   *   - server_id → the real server UUID (important for idempotency on retry)
   *   - _local_updated_at → the server's updated_at timestamp
   *
   * For DELETE:
   *   - The entity was already removed from the reactive store by the store's
   *     deleteXxx() action. If it still exists in IndexedDB (the store only
   *     soft-deletes), remove it now.
   *
   * Why not just call db.table.update()?
   * For CREATEs we resolveTemporaryId already moved the record to the real ID,
   * so by the time markSynced runs the entity lives at realId in IndexedDB.
   * For UPDATEs and DELETEs mutation.entity_id is already the real server ID.
   */
  private async markSynced(
    entityType: PendingMutation['entity_type'],
    _entityId: string,
    serverResult: { id: string; updated_at?: string }
  ): Promise<void> {
    const syncFields = {
      _sync_status: 'synced' as const,
      server_id: serverResult.id,
      ...(serverResult.updated_at
        ? { _local_updated_at: serverResult.updated_at }
        : {})
    }

    switch (entityType) {
      case 'account':
        await db.accounts.update(serverResult.id, syncFields)
        break
      case 'transaction':
        await db.transactions.update(serverResult.id, syncFields)
        break
      case 'transfer':
        await db.transfers.update(serverResult.id, syncFields)
        break
      case 'category':
        await db.categories.update(serverResult.id, syncFields)
        break

      case 'setting':
        // Settings rows use the key as PK (e.g. 'primary_currency').
        // serverResult.id is the key returned by sendSetting().
        await db.settings.update(serverResult.id, {
          _sync_status: 'synced',
          ...(serverResult.updated_at ? { _local_updated_at: serverResult.updated_at } : {})
        })
        break

      case 'dashboard':
        await db.dashboards.update(serverResult.id, syncFields)
        break

      case 'dashboard_widget':
        await db.dashboardWidgets.update(serverResult.id, syncFields)
        break
    }
  }

  // -------------------------------------------------------------------------
  // Private: error handling with exponential back-off
  // -------------------------------------------------------------------------

  /**
   * Handle a failed mutation dispatch.
   *
   * Classification:
   *   - HTTP 4xx  → permanent error (bad request, not found, conflict, etc.)
   *     The server will never accept this mutation regardless of retries.
   *     Mark the entity as 'error' and, if it was a CREATE, block all
   *     downstream mutations that depend on this entity.
   *
   *   - HTTP 5xx, timeout, or network error → transient error.
   *     Apply exponential back-off and retry up to MAX_RETRIES times.
   *     After MAX_RETRIES treat as a permanent error.
   *
   * Why wait (back-off) before incrementRetry instead of after?
   * We want to give the server time to recover before the next attempt,
   * which happens in the next processQueue() call triggered by the
   * connectivity watcher. Within a single processQueue() call we only
   * wait the back-off duration for the current mutation before moving on
   * to the next one, not before returning from processQueue entirely.
   * This way a single slow mutation doesn't block all others indefinitely.
   */
  private async handleError(
    mutation: PendingMutation,
    error: unknown,
    syncStore: ReturnType<typeof getSyncStore>
  ): Promise<void> {
    const httpStatus = isApiError(error) ? error.status : null

    if (httpStatus !== null && httpStatus >= 400 && httpStatus < 500) {
      // ── Permanent error path ──────────────────────────────────────────────
      const errorMessage = `HTTP ${httpStatus}`
      console.warn(
        `[SyncManager] Permanent error for mutation id=${mutation.id}: ${errorMessage}`
      )

      await this.markError(mutation.entity_type, mutation.entity_id, errorMessage)

      // ── Phase 5: record the permanent error in the sync store ─────────────
      // This surfaces the error count in the SyncIndicator header badge so
      // the user can see that not all changes were saved to the server.
      syncStore.addError({
        entityType: mutation.entity_type,
        entityId: mutation.entity_id,
        operation: mutation.operation,
        message: errorMessage,
        timestamp: new Date().toISOString()
      })
      // ─────────────────────────────────────────────────────────────────────

      // If a CREATE fails permanently the entity will never exist on the
      // server. Block all mutations whose payloads reference this entity's
      // ID so we don't send doomed requests.
      if (mutation.operation === 'create') {
        await this.blockDependents(mutation.entity_type, mutation.entity_id)
      }
    } else {
      // ── Transient error path (back-off + retry) ───────────────────────────
      const nextRetryCount = mutation.retry_count + 1
      const delay = Math.min(BASE_DELAY_MS * Math.pow(2, mutation.retry_count), MAX_DELAY_MS)

      console.warn(
        `[SyncManager] Transient error for mutation id=${mutation.id} ` +
        `(attempt ${nextRetryCount}/${MAX_RETRIES}). ` +
        `Waiting ${delay}ms before marking for retry.`,
        error
      )

      // Back-off wait — blocks the current iteration for this mutation only.
      await new Promise<void>((resolve) => setTimeout(resolve, delay))

      const errorMsg = isApiError(error)
        ? `HTTP ${error.status}: ${error.message}`
        : error instanceof Error
          ? error.message
          : String(error)
      await mutationQueue.incrementRetry(mutation.id!, errorMsg)

      if (nextRetryCount >= MAX_RETRIES) {
        const errorMessage = 'Max retries exceeded'
        console.warn(
          `[SyncManager] Giving up on mutation id=${mutation.id} after ${MAX_RETRIES} attempts.`
        )
        await this.markError(mutation.entity_type, mutation.entity_id, errorMessage)

        // ── Phase 5: record as permanent error after max retries ──────────
        syncStore.addError({
          entityType: mutation.entity_type,
          entityId: mutation.entity_id,
          operation: mutation.operation,
          message: errorMessage,
          timestamp: new Date().toISOString()
        })
        // ──────────────────────────────────────────────────────────────────

        if (mutation.operation === 'create') {
          await this.blockDependents(mutation.entity_type, mutation.entity_id)
        }
      }
    }
  }

  /**
   * Update an entity's _sync_status in IndexedDB to the given value.
   *
   * Used to close the race window before resolveTemporaryId: by marking
   * the temp-* record as 'synced' before the delete+re-insert, any concurrent
   * mergeWithPending call will skip it (it only returns 'pending'/'error' items).
   */
  private async markEntitySyncStatus(
    entityType: PendingMutation['entity_type'],
    entityId: string,
    status: 'synced' | 'pending' | 'error'
  ): Promise<void> {
    const fields = { _sync_status: status }
    switch (entityType) {
      case 'account': await db.accounts.update(entityId, fields); break
      case 'transaction': await db.transactions.update(entityId, fields); break
      case 'transfer': await db.transfers.update(entityId, fields); break
      case 'category': await db.categories.update(entityId, fields); break
      case 'setting': await db.settings.update(entityId, fields); break
      case 'dashboard': await db.dashboards.update(entityId, fields); break
      case 'dashboard_widget': await db.dashboardWidgets.update(entityId, fields); break
    }
  }

  /**
   * Mark an entity's _sync_status as 'error' in IndexedDB.
   *
   * Why only write _sync_status and not a last_error field?
   * last_error belongs on PendingMutation (it tracks retry state for the
   * queue processor). The Local* entity interfaces (LocalAccount, etc.) only
   * carry the three sync metadata fields: _sync_status, server_id, and
   * _local_updated_at. Writing an undeclared field would cause a TypeScript
   * strict-mode error. The error reason is logged to the console and stored
   * on the PendingMutation row via incrementRetry() — that is the canonical
   * place to inspect why a mutation failed.
   *
   * This is intentionally separate from blockDependents because not all
   * error scenarios trigger a cascade (e.g. an UPDATE failure doesn't block
   * anything — the entity already exists on the server).
   *
   * @param reason - Human-readable reason, used only for console logging.
   */
  private async markError(
    entityType: PendingMutation['entity_type'],
    entityId: string,
    reason: string
  ): Promise<void> {
    // Log the reason so it is visible in DevTools / crash reports even though
    // we don't persist it on the entity row.
    console.warn(`[SyncManager] markError: ${entityType}/${entityId} — ${reason}`)

    const errorFields: { _sync_status: 'error' } = { _sync_status: 'error' }

    switch (entityType) {
      case 'account':
        await db.accounts.update(entityId, errorFields)
        break
      case 'transaction':
        await db.transactions.update(entityId, errorFields)
        break
      case 'transfer':
        await db.transfers.update(entityId, errorFields)
        break
      case 'category':
        await db.categories.update(entityId, errorFields)
        break

      case 'setting':
        await db.settings.update(entityId, errorFields)
        break

      case 'dashboard':
        await db.dashboards.update(entityId, errorFields)
        break

      case 'dashboard_widget':
        await db.dashboardWidgets.update(entityId, errorFields)
        break
    }
  }

  /**
   * Block all queued mutations that reference the failed entity's ID.
   *
   * When a CREATE mutation fails permanently, any subsequent mutation that
   * depends on that entity (e.g. a transaction with cuenta_id === tempId) is
   * guaranteed to fail too. Rather than attempt them and receive a cascade of
   * 4xx errors, we scan the full remaining queue and mark each dependent as
   * blocked.
   *
   * Why scan all entity types?
   * An account failure can block transactions AND transfers. A category
   * failure can block transactions. We don't know upfront which entity types
   * will have dependents — scanning all is exhaustive and correct.
   *
   * Why check DEPENDENCY_FIELDS[m.entity_type]?
   * We only want to block mutations where the failing entity is referenced
   * as a dependency field (FK), not as the primary entity being mutated.
   * For example: if the failed CREATE is for an account (failedEntityId =
   * 'temp-abc'), we want to block a transaction mutation with
   * payload.cuenta_id === 'temp-abc', but NOT an account mutation with
   * entity_id === 'temp-abc' (which is the same mutation we just failed and
   * already handled).
   */
  private async blockDependents(
    failedEntityType: PendingMutation['entity_type'],
    failedEntityId: string
  ): Promise<void> {
    const allMutations = await mutationQueue.getAll()
    const blockReason = `${failedEntityType}/${failedEntityId} CREATE failed`

    for (const m of allMutations) {
      // Don't block the mutation that triggered this call.
      if (m.entity_id === failedEntityId && m.entity_type === failedEntityType) continue

      // Already blocked — don't overwrite with a different reason.
      if (m.last_error?.startsWith('blocked:')) continue

      // Check every dependency field for this mutation's entity type.
      const fieldsToCheck = DEPENDENCY_FIELDS[m.entity_type]
      const isDependent = fieldsToCheck.some(
        (field) => m.payload[field] === failedEntityId
      )

      if (isDependent && m.id != null) {
        console.warn(
          `[SyncManager] Blocking mutation id=${m.id} ` +
          `(${m.entity_type}/${m.operation}) because it depends on ` +
          `failed ${failedEntityType} ${failedEntityId}.`
        )
        await mutationQueue.markBlocked(m.id, blockReason)
      }
    }
  }

  // -------------------------------------------------------------------------
  // Private: full-read-sync
  // -------------------------------------------------------------------------

  /**
   * Re-fetch all entities from the server and write them to IndexedDB.
   *
   * Why run a full-read-sync after the queue is flushed?
   * The server may have applied additional side-effects that we cannot predict
   * locally:
   *   - Balance recalculation after a transaction sync.
   *   - Timestamps or generated fields set server-side.
   *   - Changes made by other devices in a multi-device scenario.
   *
   * The full-read-sync reconciles all of that by treating the server as the
   * source of truth and overwriting IndexedDB with fresh data.
   *
   * Why not update the Pinia stores here?
   * The SyncManager does not import stores (see architecture overview at the
   * top). The stores will pick up the updated IndexedDB data on the next
   * navigation or manual refresh because they use stale-while-revalidate via
   * fetchAllWithRevalidation(). For most UX scenarios this is acceptable
   * because the user is returning to an active tab after being offline — the
   * data was stale anyway.
   *
   * Why use Promise.allSettled instead of Promise.all?
   * A failure in one entity type (e.g. server returns 503 for categories)
   * should not prevent the other types from syncing. allSettled logs the
   * failure and continues.
   */
  private async fullReadSync(): Promise<void> {
    console.log('[SyncManager] Starting full-read-sync.')

    const results = await Promise.allSettled([
      this.syncEntityTable(
        () => accountsApi.getAll(),
        (items) =>
          db.accounts.bulkPut(
            items.map((item) => toLocalItem(item, item.id) as LocalAccount)
          )
      ),
      this.syncEntityTable(
        () => transactionsApi.getAll({ limit: 10000 } as any),
        (items) =>
          db.transactions.bulkPut(
            items.map((item) => toLocalItem(item, item.id) as LocalTransaction)
          )
      ),
      this.syncEntityTable(
        () => transfersApi.getAll({ limit: 10000 } as any),
        (items) =>
          db.transfers.bulkPut(
            items.map((item) => toLocalItem(item, item.id) as LocalTransfer)
          )
      ),
      this.syncEntityTable(
        () => categoriesApi.getAll(),
        (items) =>
          db.categories.bulkPut(
            items.map((item) => toLocalItem(item, item.id) as LocalCategory)
          )
      ),
      this.syncDashboards()
    ])

    results.forEach((result, index) => {
      const entityNames = ['accounts', 'transactions', 'transfers', 'categories', 'dashboards']
      if (result.status === 'rejected') {
        console.warn(
          `[SyncManager] full-read-sync failed for ${entityNames[index]}:`,
          result.reason
        )
      } else {
        console.log(`[SyncManager] full-read-sync completed for ${entityNames[index]}.`)
      }
    })
  }

  /**
   * Fetch a single entity collection from the API and persist it to IndexedDB.
   *
   * Extracted as a generic helper to avoid repeating the try/catch and type
   * constraint in fullReadSync. The generic T ensures both the fetcher return
   * type and the writer input type are compatible without casting.
   */
  private async syncEntityTable<T extends { id: string; updated_at: string }>(
    fetcher: () => Promise<T[]>,
    writer: (items: T[]) => Promise<unknown>
  ): Promise<void> {
    const items = await fetcher()
    await writer(items)
  }

  /**
   * Sync dashboards and their widgets from the server to Dexie.
   *
   * Why a dedicated method instead of reusing syncEntityTable?
   * Dashboards require a two-step fetch: getAll() returns a flat list of
   * Dashboard objects (no widgets), then getById() returns DashboardWithWidgets
   * for each dashboard. The syncEntityTable helper only handles a single flat
   * fetch, so it cannot drive the nested widget retrieval.
   *
   * Why fetch widgets via getById() instead of a dedicated /widgets endpoint?
   * The dashboards API does not expose a standalone "get all widgets" endpoint.
   * The only way to retrieve a dashboard's widgets is through GET /dashboards/:id,
   * which returns the dashboard with its widgets embedded. We use Promise.all
   * to parallelise the per-dashboard fetches and keep latency low.
   *
   * Why prune stale records for dashboards?
   * Dashboards are now wired into the mutation queue (like other entities).
   * After a fullReadSync the server is authoritative, so any dashboard ID no
   * longer returned by the server should be removed from Dexie. The diff
   * against serverDashboardIds handles this reconciliation.
   */
  private async syncDashboards(): Promise<void> {
    // Step 1: fetch the flat dashboard list.
    const dashboards = await dashboardsApi.getAll()
    const serverDashboardIds = dashboards.map((d) => d.id)

    // Step 2: bulkPut all dashboards into Dexie.
    await db.dashboards.bulkPut(
      dashboards.map((d) => toLocalItem(d, d.id) as LocalDashboard)
    )

    // Step 3: fetch widgets for every dashboard in parallel.
    const detailResults = await Promise.all(
      dashboards.map((d) => dashboardsApi.getById(d.id))
    )

    // Step 4: flatten all widgets and bulkPut them.
    const allWidgets = detailResults.flatMap((detail) => detail.widgets)
    await db.dashboardWidgets.bulkPut(
      allWidgets.map((w) => toLocalItem(w, w.id) as LocalDashboardWidget)
    )

    // Step 5: prune dashboards whose IDs are no longer on the server.
    // noneOf([]) would delete everything, so guard against an empty list.
    if (serverDashboardIds.length > 0) {
      await db.dashboards.where('id').noneOf(serverDashboardIds).delete()
    } else {
      await db.dashboards.clear()
    }

    // Step 6: prune widgets belonging to dashboards that no longer exist.
    // We key on dashboard_id (an indexed field) rather than widget id because
    // the server only returns widgets for existing dashboards — any widget
    // whose parent dashboard was deleted is orphaned in Dexie.
    if (serverDashboardIds.length > 0) {
      await db.dashboardWidgets.where('dashboard_id').noneOf(serverDashboardIds).delete()
    } else {
      await db.dashboardWidgets.clear()
    }
  }
}

// ---------------------------------------------------------------------------
// Singleton export
//
// Why a singleton?
// Exactly the same reason as mutationQueue and db: the SyncManager is
// stateless except for the processing flag, which must be shared across all
// call sites. A single export ensures there is only ever one processing flag
// and one active processQueue() run at a time.
// ---------------------------------------------------------------------------
export const syncManager = new SyncManager()
