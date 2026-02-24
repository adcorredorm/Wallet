/**
 * MutationQueue — FIFO queue of pending write operations
 *
 * Why a dedicated class instead of calling db.pendingMutations directly?
 * The queue has non-trivial logic: FIFO ordering, the create+update merge
 * optimisation, and the create+delete cancellation optimisation. Encapsulating
 * all of that here keeps the stores thin and makes this logic independently
 * testable in Phase 4.
 *
 * Why FIFO ordered by queued_at?
 * Causality must be preserved when replaying mutations against the server.
 * Consider: create account (temp-abc) → create transaction on temp-abc.
 * If the sync engine processes the transaction first, the server will reject it
 * because the account does not exist yet. Strict FIFO prevents this class of
 * dependency violation.
 *
 * Why retry_count + last_error?
 * The sync engine (Phase 4) will implement exponential back-off. It needs to
 * know how many times a mutation has been attempted and what the last failure
 * was so it can decide when to give up and surface the error to the user.
 *
 * Why the create+update merge optimisation?
 * If the user creates a record offline and then immediately edits it (still
 * offline), naively we would have two queue entries: a CREATE and an UPDATE.
 * On sync, we would send a POST then a PATCH — two round-trips. The merge
 * collapses both into a single POST with the final field values, reducing
 * network overhead and server-side complexity.
 *
 * Why the create+delete cancellation optimisation?
 * If the user creates a record offline and then deletes it before syncing,
 * the entity never existed on the server. There is no reason to send anything
 * at all. We cancel both mutations locally and skip the sync entirely.
 */

import { db } from './db'
import type { PendingMutation } from './types'

export class MutationQueue {
  /**
   * Enqueue a new pending mutation.
   *
   * queued_at is set here (not by the caller) to guarantee that the ordering
   * timestamp reflects the true wall-clock insertion time, not a timestamp that
   * may have been constructed earlier in the call stack.
   *
   * retry_count starts at 0. The sync engine increments it via incrementRetry()
   * each time a flush attempt fails.
   *
   * @returns The auto-incremented integer ID assigned by Dexie/IndexedDB.
   */
  async enqueue(
    mutation: Omit<PendingMutation, 'id' | 'queued_at' | 'retry_count'>
  ): Promise<number> {
    const id = await db.pendingMutations.add({
      ...mutation,
      queued_at: new Date().toISOString(),
      retry_count: 0
    })
    // Signal main.ts to trigger SyncManager if the device is currently online.
    // This ensures mutations are flushed to the server immediately rather than
    // waiting for the next connectivity-change event.
    window.dispatchEvent(new CustomEvent('wallet:mutation-queued'))
    return id
  }

  /**
   * Return all pending mutations ordered by queued_at ascending (FIFO).
   *
   * Why orderBy('queued_at') instead of relying on the auto-increment id?
   * The auto-increment id is also a valid FIFO proxy in a single-device
   * scenario, but queued_at makes the ordering intent explicit and lets
   * Phase 4 implement time-based conflict resolution if needed.
   */
  async getAll(): Promise<PendingMutation[]> {
    return db.pendingMutations.orderBy('queued_at').toArray()
  }

  /**
   * Find a pending CREATE mutation for a specific entity.
   *
   * Used by the create+update merge and create+delete cancellation
   * optimisations in the store write actions.
   *
   * Why use where('entity_id').equals() instead of a compound where()?
   * The db.ts schema defines individual indexes for entity_type, entity_id,
   * and operation, but NOT a compound index like [entity_type+entity_id+operation].
   * Dexie's object-form where({ a, b, c }) requires an explicit compound index to
   * work as a single index lookup; without it, Dexie v3+ throws or falls back to a
   * full table scan.
   *
   * Instead, we use the entity_id index (the most selective field — one record
   * per entity that was created offline) to narrow the result set, then filter
   * the remaining two conditions in memory. Because entity_id values are UUIDs
   * the filtered set will almost always be a single row, so the in-memory
   * filter cost is negligible.
   *
   * Returns undefined if no such CREATE exists (meaning the entity was
   * already synced to the server and only an UPDATE or DELETE is needed).
   */
  async findPendingCreate(
    entityType: PendingMutation['entity_type'],
    entityId: string
  ): Promise<PendingMutation | undefined> {
    // Step 1: index lookup on entity_id (narrows to at most a handful of rows).
    const candidates = await db.pendingMutations
      .where('entity_id')
      .equals(entityId)
      .toArray()

    // Step 2: in-memory filter for entity_type and operation.
    return candidates.find(
      m => m.entity_type === entityType && m.operation === 'create'
    )
  }

  /**
   * Replace the payload of an existing mutation.
   *
   * Used exclusively by the create+update merge: after finding a pending
   * CREATE we overwrite its payload with the merged (create + update) data
   * so a single POST to the server is sufficient.
   */
  async updatePayload(id: number, payload: Record<string, unknown>): Promise<void> {
    await db.pendingMutations.update(id, { payload })
  }

  /**
   * Remove a mutation from the queue permanently.
   *
   * Called in two situations:
   * 1. The sync engine successfully flushed the mutation to the server.
   * 2. The create+delete cancellation optimisation: the CREATE is removed
   *    and no DELETE is enqueued because the entity never reached the server.
   */
  async remove(id: number): Promise<void> {
    await db.pendingMutations.delete(id)
  }

  /**
   * Count total pending mutations.
   *
   * Used by the UI sync status badge (Phase 4) to show the user how many
   * changes are waiting to be uploaded.
   */
  async count(): Promise<number> {
    return db.pendingMutations.count()
  }

  /**
   * Mark a mutation as blocked due to a dependency failure.
   *
   * When the sync engine encounters a failed CREATE for entity A, all
   * subsequent mutations that reference entity A (e.g. transactions with
   * cuenta_id === tempId) must be blocked rather than retried, because they
   * will keep failing as long as A doesn't exist on the server.
   *
   * The 'blocked: ' prefix in last_error lets the sync engine distinguish
   * blocking errors from transient network errors at a glance.
   */
  async markBlocked(id: number, reason: string): Promise<void> {
    await db.pendingMutations.update(id, { last_error: `blocked: ${reason}` })
  }

  /**
   * Increment the retry counter and record the error message.
   *
   * The sync engine calls this after each failed attempt before scheduling
   * the next retry with exponential back-off. We read the current record to
   * get the existing retry_count rather than doing a blind increment, which
   * would require an IndexedDB compound update that Dexie does not support
   * in a single call.
   */
  async incrementRetry(id: number, errorMessage: string): Promise<void> {
    const mutation = await db.pendingMutations.get(id)
    if (mutation) {
      await db.pendingMutations.update(id, {
        retry_count: mutation.retry_count + 1,
        last_error: errorMessage
      })
    }
  }
}

/**
 * Singleton instance.
 *
 * Shared across all stores and the sync engine (Phase 4) so that all queue
 * operations happen through the same in-memory object. This is safe because
 * MutationQueue is stateless — every method goes straight to IndexedDB.
 */
export const mutationQueue = new MutationQueue()
