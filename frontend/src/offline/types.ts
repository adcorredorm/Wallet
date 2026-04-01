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
import type { Dashboard, DashboardWidget } from '@/types/dashboard'
import type { RecurringRule } from '@/types/recurring-rule'
import type { Budget } from '@/types/budget'

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
  original_amount?: number    // Amount in the original currency before conversion
  original_currency?: string  // ISO 4217 code of the original currency (e.g. 'COP')
  exchange_rate?: number      // Rate applied at the time of the transaction
  base_rate?: number | null   // Units of primaryCurrency per 1 unit of account.currency at capture time; null when offline with no cached rate
  recurring_rule_id?: string | null  // FK -> recurringRules (offline or server ID)
}

export interface LocalTransfer extends Transfer {
  server_id?: string
  _sync_status: SyncStatus
  _local_updated_at: string
  destination_amount?: number   // Amount received in the destination account (may differ due to FX)
  exchange_rate?: number        // Rate applied at the time of the transfer
  destination_currency?: string // ISO 4217 code of the destination account's currency
  base_rate?: number | null     // Units of primaryCurrency per 1 unit of source_account.currency at capture time; null when offline with no cached rate
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
  id?: number                                                                    // Auto-incremented by Dexie (undefined before first insert)
  entity_type: 'account' | 'transaction' | 'transfer' | 'category' | 'setting' | 'dashboard' | 'dashboard_widget' | 'recurring_rule' | 'budget'
  entity_id: string                                                              // Local ID (may be a temp-* UUID)
  operation: 'create' | 'update' | 'delete' | 'delete_permanent'
  payload: Record<string, unknown>                                  // Serialised DTO
  queued_at: string                                                 // ISO timestamp — FIFO ordering key
  retry_count: number
  last_error?: string
}

/**
 * LocalExchangeRate — a cached foreign-exchange rate stored locally.
 *
 * Why no _sync_status?
 * Exchange rates are fetched from external APIs (exchangerate.host,
 * CoinGecko, etc.) and replaced wholesale. There is no concept of a
 * "pending" local mutation to sync back to the server — the server itself
 * fetches and caches these from the same sources. Therefore LWW sync
 * fields are not needed here.
 *
 * Why currency_code as PK?
 * There is at most one rate per currency at any given time. Using the ISO
 * 4217 code (or ticker for crypto) as the primary key means a simple
 * table.put() is both an insert and an upsert — no duplicate-rate logic
 * needed in the consuming code.
 */
export interface LocalExchangeRate {
  currency_code: string // PK — ISO 4217 code or crypto ticker, e.g. 'USD', 'BTC'
  rate_to_usd: number   // Units of this currency per 1 USD
  source: string        // 'exchangerate.host' | 'coingecko' | 'system'
  fetched_at: string    // ISO timestamp of the last remote fetch
  updated_at: string    // ISO timestamp of the last local write
}

/**
 * LocalSetting — a key/value store for user-configurable settings.
 *
 * Why offline-first with _sync_status?
 * Settings like 'primary_currency' are user choices that should survive
 * offline usage and sync back to the server when connectivity returns,
 * exactly like accounts and transactions. LWW resolution via
 * _local_updated_at ensures the most recent change wins during sync.
 *
 * Why `value: unknown` instead of `value: string`?
 * Different settings carry different value shapes — a currency code is a
 * string, a display precision is a number, a feature flag is a boolean.
 * Using `unknown` forces callers to narrow the type explicitly, which is
 * safer than casting to `any`.
 */
export interface LocalSetting {
  key: string              // PK — e.g. 'primary_currency', 'display_precision'
  value: unknown           // JSON value narrowed by the caller
  updated_at: string       // ISO timestamp of the last server sync
  _sync_status: SyncStatus // Offline-first sync state (same pattern as other entities)
  _local_updated_at: string // ISO timestamp for LWW conflict resolution
}

export interface LocalDashboard extends Dashboard {
  server_id?: string
  _sync_status: SyncStatus
  _local_updated_at: string
}

export interface LocalDashboardWidget extends DashboardWidget {
  server_id?: string
  _sync_status: SyncStatus
  _local_updated_at: string
}

export interface LocalRecurringRule extends RecurringRule {
  server_id?: string
  _sync_status: SyncStatus
  _local_updated_at: string
}

export interface LocalBudget extends Budget {
  server_id?: string
  _sync_status: SyncStatus
  _local_updated_at: string
}

export type PendingOccurrenceStatus = 'pending' | 'confirmed' | 'discarded' | 'expired'

export interface LocalPendingOccurrence {
  id: string                        // client-generated UUID
  recurring_rule_id: string         // FK -> LocalRecurringRule
  due_date: string                  // YYYY-MM-DD
  suggested_amount: number          // copied from rule at generation time
  status: PendingOccurrenceStatus
  created_at: string                // ISO timestamp
}
