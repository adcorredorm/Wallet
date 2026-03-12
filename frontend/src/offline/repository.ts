/**
 * Offline Repository — stale-while-revalidate data access layer
 *
 * This module sits between the Pinia stores and both the API layer and
 * IndexedDB. It implements a strict stale-while-revalidate (SWR) pattern:
 *
 *   1. Return data from IndexedDB immediately — even if the cache is empty.
 *      The UI renders right away (empty state / skeleton while waiting).
 *   2. If online, fetch fresh data from the API in the background.
 *   3. Persist fresh data to IndexedDB and invoke onFreshData so the store
 *      can update its reactive state.
 *
 * Design principle: IndexedDB is always the source of truth for the initial
 * render. The API is always a background operation. There is no blocking
 * cold-start path — the UI is never held waiting for a network response.
 *
 * Why separate from the stores?
 * Keeping this logic here means the stores stay focused on reactive state
 * management (what Vue cares about) while this file owns the I/O concerns
 * (IndexedDB + network). Easier to test each layer independently.
 *
 * Why call useOnline() at module level?
 * VueUse 10+ initialises useOnline() with a global window 'online'/'offline'
 * event listener the first time it is called. Subsequent calls return the
 * same shared Ref<boolean>. Calling it at module level (outside setup()) is
 * valid and avoids re-subscribing on every store action invocation.
 */

import { useOnline } from '@vueuse/core'
import type { Table } from 'dexie'
import type { SyncStatus } from './types'

// One shared online indicator for the entire offline module.
const isOnline = useOnline()

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/**
 * Map a raw server item to its local representation by adding the three
 * sync metadata fields.
 *
 * Why 'synced' + server's updated_at?
 * - _sync_status: 'synced' because this data came directly from the server.
 * - _local_updated_at: we use the server's own updated_at so that if the
 *   user edits the record offline, the local timestamp will be newer than
 *   the server timestamp, making LWW conflict resolution straightforward.
 */
function toLocalItem<T extends { id: string; updated_at: string }>(
  item: T
): T & { _sync_status: SyncStatus; _local_updated_at: string } {
  return {
    ...item,
    _sync_status: 'synced' as const,
    _local_updated_at: item.updated_at
  }
}

/**
 * Merge server items with any locally-pending records that the server does
 * not yet know about.
 *
 * Why is this merge necessary?
 * When a record is created offline it receives a temp-* ID and
 * _sync_status: 'pending'. It lives in IndexedDB but has never reached the
 * server. When background revalidation succeeds, the server response does not
 * include the pending record (the server has never seen it). Without this
 * merge, passing the raw server list to onFreshData would replace the entire
 * reactive array and the pending record would disappear from the UI — even
 * though it is safely stored in IndexedDB and queued for upload.
 *
 * The merge rule:
 *   - Keep all server items (they are the authoritative synced state).
 *   - Append any local items whose _sync_status is 'pending' or 'error' AND
 *     whose id is NOT already present in the server response. This preserves
 *     offline-created records in the reactive list until they are synced.
 *
 * Why filter by id not in server response?
 * If a pending record was synced by another path (e.g. the SyncManager ran
 * just before this revalidation completed) the server will include it under
 * its real UUID and the temp-* row will have been replaced in IndexedDB.
 * Checking by server-response ID set prevents accidental duplication.
 */
async function mergeWithPending<
  TLocal extends { id: string; _sync_status: SyncStatus }
>(
  table: Table<TLocal>,
  serverItems: TLocal[]
): Promise<TLocal[]> {
  // Build a fast O(1) lookup set of all IDs already present in the server
  // response. IDs are real server UUIDs — temp-* IDs will never appear here.
  const serverIds = new Set(serverItems.map((item) => item.id))

  // Read only the pending/error rows from IndexedDB. Using the _sync_status
  // index (defined in db.ts) makes this an O(log n) scan rather than a full
  // table scan.
  const pendingLocal = await table
    .where('_sync_status')
    .anyOf(['pending', 'error'])
    .toArray()

  // Keep only those pending records that the server response does not already
  // cover (i.e. they have not been synced yet).
  const unsyncedLocal = pendingLocal.filter((item) => !serverIds.has(item.id))

  return [...serverItems, ...unsyncedLocal]
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Fetch all records for an entity using stale-while-revalidate.
 *
 * @param table       - Dexie table to read from / write to.
 * @param apiFetcher  - Async function that calls the remote API.
 * @param onFreshData - Callback invoked with fresh server data (merged with
 *                      any locally pending records) after background
 *                      revalidation succeeds. The store uses this to update
 *                      its reactive ref.
 *
 * @returns           The locally-cached array. May be empty on first load
 *                    (cold start) — the store should show a loading/empty
 *                    state and wait for onFreshData to provide real data.
 *
 * Error behaviour:
 * - API errors are always swallowed with a console.warn. The store's error
 *   state is never set by a background revalidation failure; the UI simply
 *   continues showing whatever IndexedDB has (which may be empty).
 */
export async function fetchAllWithRevalidation<
  TServer extends { id: string; updated_at: string },
  TLocal extends TServer & { _sync_status: SyncStatus }
>(
  table: Table<TLocal>,
  apiFetcher: () => Promise<TServer[]>,
  onFreshData: (freshItems: TLocal[]) => void
): Promise<TLocal[]> {
  // Step 1 — Read from IndexedDB immediately (no network round-trip).
  // This is what makes the UI feel instant. The result may be an empty array
  // on the very first load — that is intentional and expected.
  const localData = await table.toArray()

  // Step 2 — Fire background revalidation when online.
  // We never await this: IndexedDB data (even if empty) is returned right away
  // and the UI updates reactively when the background fetch completes.
  if (isOnline.value) {
    ;(async () => {
      try {
        const serverItems = await apiFetcher()
        const localMapped = serverItems.map(toLocalItem) as unknown as TLocal[]

        // Skip records that are locally pending/error — those represent
        // user changes the server has not yet received. Overwriting them with
        // stale server data would silently discard the user's edits.
        const pendingIds = new Set(
          await table.where('_sync_status').anyOf(['pending', 'error']).primaryKeys()
        )
        const itemsToWrite = localMapped.filter((item) => !pendingIds.has(item.id as never))
        await table.bulkPut(itemsToWrite)

        // Remove orphaned synced records: items in IndexedDB that the server
        // no longer returns AND are not pending local changes. These are stale
        // records (e.g. deleted server-side, or left over from test data).
        const serverIds = new Set(localMapped.map((item) => item.id))
        const orphanedIds = (await table.where('_sync_status').anyOf(['synced', 'error']).primaryKeys())
          .filter((id) => !serverIds.has(id as string))
        if (orphanedIds.length > 0) await table.bulkDelete(orphanedIds)

        // Re-read the full table from IndexedDB after bulkPut.
        //
        // Why table.toArray() instead of mergeWithPending(table, localMapped)?
        // mergeWithPending only appends 'pending'/'error' rows to the server
        // response. This fails when:
        //   1. The SyncManager runs fullReadSync between when this GET was
        //      dispatched and when it completes. fullReadSync writes newly-synced
        //      records (now '_sync_status: synced') to IndexedDB, but this GET's
        //      stale server response doesn't include them → mergeWithPending
        //      finds no pending items and the records disappear from the UI.
        //   2. An offline-created record is synced (no longer 'pending') during
        //      the same window.
        //
        // table.toArray() is always the correct view: it includes server items
        // just written by bulkPut, any still-pending local items, AND any records
        // written by fullReadSync — the full authoritative local state.
        const freshFromDB = await table.toArray()

        // Notify the store so its reactive ref gets the fresh data.
        onFreshData(freshFromDB)
      } catch (err) {
        // Background revalidation errors are never fatal. The user sees their
        // cached data (or an empty state on cold start) and the SyncManager
        // will retry when conditions improve.
        console.warn('[offline/repository] Background revalidation failed:', err)
      }
    })()
  }

  return localData
}

/**
 * Fetch a single record by primary key using stale-while-revalidate.
 *
 * Follows the same always-background pattern as fetchAllWithRevalidation
 * but for a single item identified by its ID.
 *
 * @param table       - Dexie table to read from / write to.
 * @param id          - Primary key of the record.
 * @param apiFetcher  - Async function that calls the remote API for this ID.
 * @param onFreshData - Callback invoked with the fresh item after revalidation.
 *
 * @returns           The locally-cached item, or undefined if not yet in
 *                    IndexedDB. onFreshData will provide the item once the
 *                    background fetch completes.
 */
export async function fetchByIdWithRevalidation<
  TServer extends { id: string; updated_at: string },
  TLocal extends TServer
>(
  table: Table<TLocal>,
  id: string,
  apiFetcher: (id: string) => Promise<TServer>,
  onFreshData: (freshItem: TLocal) => void
): Promise<TLocal | undefined> {
  // Step 1 — Fast local read by primary key (O(log n) index lookup).
  const localItem = await table.get(id)

  // Step 2 — Background revalidation (always fire-and-forget).
  if (isOnline.value) {
    ;(async () => {
      try {
        const serverItem = await apiFetcher(id)
        const localMapped = toLocalItem(serverItem) as unknown as TLocal
        await table.put(localMapped)
        onFreshData(localMapped)
      } catch (err) {
        console.warn(`[offline/repository] Background revalidation failed for id=${id}:`, err)
      }
    })()
  }

  return localItem
}
