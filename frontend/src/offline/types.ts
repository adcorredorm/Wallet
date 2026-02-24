/**
 * Offline / Local persistence type definitions
 *
 * Why extend rather than wrap?
 * Each Local* interface extends the server-side domain type directly. This
 * means a LocalAccount is still a valid Account everywhere in the codebase.
 * Components that read `accounts.value` continue to work without changes
 * because the extra _sync_* fields are additive, not breaking.
 *
 * Why three sync fields?
 * - server_id:         Tracks the real UUID assigned by the server. undefined
 *                      when the record was created offline and hasn't been
 *                      synced yet. Phase 3 will populate this on first sync.
 * - _sync_status:      Drives the sync queue logic in Phase 3. 'synced' means
 *                      the local copy matches the server. 'pending' means a
 *                      mutation is queued. 'error' means the last sync attempt
 *                      failed.
 * - _local_updated_at: ISO timestamp copied from server updated_at on reads,
 *                      or set to Date.now() on local mutations. Used for
 *                      Last-Write-Wins (LWW) conflict resolution in Phase 3.
 */

import type { Account } from '@/types/account'
import type { Transaction } from '@/types/transaction'
import type { Transfer } from '@/types/transfer'
import type { Category } from '@/types/category'

// Union literal — intentionally not an enum so it can be used as a plain
// string comparison without a runtime import.
export type SyncStatus = 'synced' | 'pending' | 'error'

export interface LocalAccount extends Account {
  server_id?: string        // Real UUID from the server (undefined if created offline)
  _sync_status: SyncStatus  // Current sync state
  _local_updated_at: string // ISO timestamp for LWW conflict resolution
}

export interface LocalTransaction extends Transaction {
  server_id?: string
  _sync_status: SyncStatus
  _local_updated_at: string
}

export interface LocalTransfer extends Transfer {
  server_id?: string
  _sync_status: SyncStatus
  _local_updated_at: string
}

export interface LocalCategory extends Category {
  server_id?: string
  _sync_status: SyncStatus
  _local_updated_at: string
}

/**
 * PendingMutation — a serialised write operation waiting to be sent to the API.
 *
 * Why FIFO with queued_at?
 * Mutations must be replayed in the order they were created to preserve
 * causality. For example: create account → create transaction on that account.
 * If both are pending and we send the transaction first, the server will reject
 * it because the account doesn't exist yet.
 *
 * Why retry_count + last_error?
 * These fields support exponential back-off in Phase 3 and give the user
 * feedback when a specific mutation keeps failing.
 */
export interface PendingMutation {
  id?: number                                                       // Auto-incremented by Dexie (undefined before first insert)
  entity_type: 'account' | 'transaction' | 'transfer' | 'category'
  entity_id: string                                                 // Local ID (may be a temp-* UUID)
  operation: 'create' | 'update' | 'delete'
  payload: Record<string, unknown>                                  // Serialised DTO
  queued_at: string                                                 // ISO timestamp — FIFO ordering key
  retry_count: number
  last_error?: string
}
