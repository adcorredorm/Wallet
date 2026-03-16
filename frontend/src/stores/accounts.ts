/**
 * Accounts Store
 *
 * Why Pinia with Composition API?
 * - Type-safe state management with TypeScript
 * - More intuitive than Vuex (no mutations, simpler actions)
 * - Better DevTools integration
 * - Lightweight and modular
 *
 * This store manages:
 * - Account list and selection
 * - Account balances (computed locally from IndexedDB — never fetched from backend)
 * - CRUD operations for accounts
 *
 * Phase 3 change: write actions (create/update/delete) now follow the
 * offline-first pattern — they write to IndexedDB and the mutation queue
 * immediately, before touching the network. The UI updates without waiting
 * for a server round-trip. The SyncManager (Phase 4) will flush the queue
 * when connectivity is restored.
 *
 * Archive/hard-delete change:
 * - archiveAccount (formerly deleteAccount): sets active=false in IndexedDB
 *   instead of removing the record. The archived account stays in IndexedDB
 *   so it can be restored and so its balance history is preserved locally.
 *   Backend interprets the DELETE verb as a soft-delete (archive).
 * - hardDeleteAccount: permanently removes the record from IndexedDB and
 *   enqueues a delete_permanent mutation so the backend also hard-deletes.
 *   Only allowed when the account has no transactions or transfers.
 * - restoreAccount: flips active back to true and enqueues an update mutation.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { accountsApi } from '@/api/accounts'
import type { CreateAccountDto, UpdateAccountDto, AccountBalance } from '@/types'
import { db, fetchByIdWithRevalidation, generateTempId, mutationQueue } from '@/offline'
import type { LocalAccount } from '@/offline'

export const useAccountsStore = defineStore('accounts', () => {
  // State
  // Why LocalAccount[] instead of Account[]?
  // LocalAccount extends Account, so all existing consumers of this ref
  // (computed properties, components) continue to work without changes.
  // The extra _sync_* fields are additive.
  const accounts = ref<LocalAccount[]>([])
  const balances = ref<Map<string, AccountBalance>>(new Map())
  const selectedAccountId = ref<string | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Computed
  const activeAccounts = computed(() =>
    accounts.value.filter(account => account.active)
  )

  // Why filter active === false rather than !active?
  // active is always a boolean on LocalAccount (required field on Account).
  // Strict equality guards against undefined on records fetched from older
  // IndexedDB schema versions that pre-date the active column.
  const archivedAccounts = computed(() =>
    accounts.value.filter(account => account.active === false)
  )

  const selectedAccount = computed(() =>
    accounts.value.find(account => account.id === selectedAccountId.value) || null
  )

  const accountsWithBalances = computed(() =>
    accounts.value.map(account => ({
      ...account,
      // Prefer balances.value (updated by adjustBalance on every write and by
      // recomputeBalancesFromTransactions after sync). Falls back to
      // account.balance from IndexedDB (persisted by adjustBalance on writes).
      balance: balances.value.get(account.id)?.balance ?? account.balance ?? 0
    }))
  )

  // ---------------------------------------------------------------------------
  // Helper: normalise balance field from API (may arrive as string)
  // ---------------------------------------------------------------------------
  function normalizeBalance(account: LocalAccount): LocalAccount {
    return {
      ...account,
      balance: account.balance !== undefined ? Number(account.balance) : 0
    }
  }

  // ---------------------------------------------------------------------------
  // Actions — Reads (offline-first, stale-while-revalidate)
  // ---------------------------------------------------------------------------

  async function fetchAccounts() {
    loading.value = true
    error.value = null
    try {
      await refreshFromDB()
    } catch (err: any) {
      error.value = err.message || 'Error al cargar cuentas'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchAccountById(id: string) {
    loading.value = true
    error.value = null
    try {
      const localItem = await fetchByIdWithRevalidation(
        db.accounts,
        id,
        (accountId) => accountsApi.getById(accountId),
        (freshItem) => {
          // Background revalidation callback: update the specific entry.
          // Balance comes from IndexedDB (persisted by adjustBalance) — no
          // backend balance endpoint call needed.
          const normalized = normalizeBalance(freshItem)
          const index = accounts.value.findIndex(a => a.id === id)
          if (index >= 0) {
            // Preserve the locally-tracked balance so the server's list value
            // (which may be stale for pending transactions) doesn't overwrite it.
            const localBalance = balances.value.get(id)?.balance
                               ?? accounts.value.find(a => a.id === id)?.balance
            accounts.value[index] = {
              ...normalized,
              balance: localBalance ?? normalized.balance
            }
          } else {
            accounts.value.push(normalized)
          }
        }
      )

      if (localItem) {
        const normalized = normalizeBalance(localItem)
        const index = accounts.value.findIndex(a => a.id === id)
        if (index >= 0) {
          accounts.value[index] = normalized
        } else {
          accounts.value.push(normalized)
        }
        return normalized
      }
    } catch (err: any) {
      error.value = err.message || 'Error al cargar cuenta'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Recompute every account's balance from the local transaction and transfer
   * history stored in IndexedDB.
   *
   * Why compute locally instead of calling the /balance API endpoint?
   * The frontend is a standalone app — IndexedDB is the single source of
   * truth for ALL displayed data. Backend endpoints are used only for
   * synchronisation (pushing local mutations, pulling server writes from
   * other devices). The /balance endpoint is unreliable for display because
   * it doesn't include pending offline transactions that haven't synced yet.
   *
   * When to call this:
   *   After wallet:sync-complete — at that point fullReadSync has loaded the
   *   complete transaction history into IndexedDB so the computed total is
   *   authoritative and identical to what the server would return.
   */
  async function recomputeBalancesFromTransactions() {
    const allTransactions = await db.transactions.toArray()
    const allTransfers   = await db.transfers.toArray()

    const computed = new Map<string, number>()

    for (const tx of allTransactions) {
      const current = computed.get(tx.account_id) ?? 0
      const delta = tx.type === 'income' ? Number(tx.amount) : -Number(tx.amount)
      computed.set(tx.account_id, current + delta)
    }

    for (const t of allTransfers) {
      // Source account always loses `amount` (what was sent, in source currency).
      const fromBal = computed.get(t.source_account_id) ?? 0
      computed.set(t.source_account_id, fromBal - Number(t.amount))
      // Destination account gains `destination_amount` for cross-currency transfers,
      // or falls back to `amount` for same-currency transfers where destination_amount
      // is undefined. This mirrors the adjustBalance logic in the transfers store.
      const toBal = computed.get(t.destination_account_id) ?? 0
      computed.set(
        t.destination_account_id,
        toBal + Number(t.destination_amount ?? t.amount)
      )
    }

    for (const [accountId, balance] of computed) {
      const account = accounts.value.find(a => a.id === accountId)
      balances.value.set(accountId, {
        account_id: accountId,
        balance,
        currency: account?.currency ?? 'USD'
      })
      const idx = accounts.value.findIndex(a => a.id === accountId)
      if (idx !== -1) {
        accounts.value[idx] = { ...accounts.value[idx], balance }
      }
      // Persist so the recomputed balance survives the next page reload.
      await db.accounts.update(accountId, { balance })
    }
  }

  // ---------------------------------------------------------------------------
  // Actions — Writes (Phase 3: offline-first pattern)
  //
  // Every write method follows the same three-step sequence:
  //   1. Persist the change to IndexedDB immediately so data survives a reload.
  //   2. Update the reactive ref so the UI reflects the change without waiting
  //      for a network round-trip (optimistic UI).
  //   3. Enqueue a PendingMutation so the SyncManager (Phase 4) can replay
  //      the operation against the server when connectivity is available.
  //
  // The `loading` flag is still set so existing UI spinners continue to work.
  // Because IndexedDB writes are very fast (sub-millisecond in practice),
  // the spinner will barely be visible — but we keep it for consistency with
  // the read actions and to give the UI a hook for any future async work.
  // ---------------------------------------------------------------------------

  async function createAccount(data: CreateAccountDto) {
    // Why generateTempId()?
    // We need a stable local identifier for the new record before the server
    // assigns a real UUID. The 'temp-' prefix lets the SyncManager distinguish
    // locally-created records from server-synced ones at a glance (O(1) check
    // via isTempId()) without an extra database lookup.
    const tempId = generateTempId()
    const now = new Date().toISOString()

    // Build the full local representation of the account.
    // Required fields that the server would normally fill in are given sensible
    // defaults:
    //   - tags: CreateAccountDto.tags is optional, default to empty array.
    //   - active: new accounts are always active.
    //   - balance: 0 until the first transaction is recorded.
    //   - _sync_status: 'pending' signals that this record has an unsent mutation.
    //   - _local_updated_at: used for Last-Write-Wins conflict resolution.
    const localAccount: LocalAccount = {
      id: tempId,
      name: data.name,
      type: data.type,
      currency: data.currency,
      description: data.description,
      tags: data.tags ?? [],
      active: true,
      balance: 0,
      created_at: now,
      updated_at: now,
      _sync_status: 'pending',
      _local_updated_at: now
    }

    loading.value = true
    error.value = null
    try {
      // Step 1 — Write to IndexedDB. This is the source of truth for offline
      // data. If the app closes before sync, the record is preserved here.
      await db.accounts.add(localAccount)

      // Step 2 — Update the reactive ref. Vue re-renders immediately without
      // waiting for the network. The user sees their new account right away.
      accounts.value.push(localAccount)

      // Seed the balances map so accountsWithBalances computed doesn't show
      // undefined for the new account.
      balances.value.set(tempId, {
        account_id: tempId,
        balance: 0,
        currency: data.currency
      })

      // Step 3 — Enqueue the CREATE mutation.
      // client_id in the payload is the same tempId so the backend can use it
      // for idempotency: if the same mutation is replayed due to a network
      // timeout, the server detects the duplicate client_id and returns the
      // already-created account rather than creating a second one.
      await mutationQueue.enqueue({
        entity_type: 'account',
        entity_id: tempId,
        operation: 'create',
        payload: { ...data, client_id: tempId }
      })

      return localAccount
    } catch (err: any) {
      error.value = err.message || 'Error al crear cuenta'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateAccount(id: string, data: UpdateAccountDto) {
    const localUpdatedAt = new Date().toISOString()

    loading.value = true
    error.value = null
    try {
      // Step 1 — Patch the IndexedDB record.
      // We use Dexie's update() which does a partial update (like PATCH),
      // only overwriting the fields present in the object literal. The
      // _sync_status and _local_updated_at metadata fields are always included
      // to mark this record as dirty for the sync engine.
      await db.accounts.update(id, {
        ...data,
        _sync_status: 'pending',
        _local_updated_at: localUpdatedAt
      })

      // Step 2 — Update the reactive ref.
      // Object spread preserves all existing fields on the record so we don't
      // accidentally lose fields that are not part of UpdateAccountDto
      // (e.g. created_at, server_id).
      const idx = accounts.value.findIndex(a => a.id === id)
      if (idx !== -1) {
        accounts.value[idx] = {
          ...accounts.value[idx],
          ...data,
          _sync_status: 'pending',
          _local_updated_at: localUpdatedAt
        }
      }

      // Step 3 — Merge optimisation: if there is already a pending CREATE for
      // this entity, collapse the UPDATE into the CREATE payload instead of
      // adding a second queue entry. This reduces the sync to a single POST
      // instead of POST + PATCH.
      const pendingCreate = await mutationQueue.findPendingCreate('account', id)
      if (pendingCreate && pendingCreate.id != null) {
        await mutationQueue.updatePayload(pendingCreate.id, {
          ...pendingCreate.payload,
          ...data
        })
      } else {
        // No pending CREATE — the entity exists on the server. Enqueue a
        // normal UPDATE mutation that the sync engine will send as a PATCH.
        await mutationQueue.enqueue({
          entity_type: 'account',
          entity_id: id,
          operation: 'update',
          payload: data as Record<string, unknown>
        })
      }
    } catch (err: any) {
      error.value = err.message || 'Error al actualizar cuenta'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Archive an account — soft-delete that keeps the record in IndexedDB with
   * active=false. The account moves from activeAccounts to archivedAccounts
   * in the UI. The backend treats DELETE as a soft-delete (archive).
   *
   * Why keep in IndexedDB instead of removing?
   * Archived accounts must be restorable. They also retain their balance
   * history so net worth calculations remain accurate. Physical removal would
   * lose that history on the next page reload.
   *
   * Special case: if the account was created offline and never synced
   * (pending CREATE in queue), archive is equivalent to cancellation —
   * we remove the record entirely and cancel the CREATE mutation instead
   * of enqueuing a DELETE, because the server never knew about this account.
   */
  async function archiveAccount(id: string) {
    loading.value = true
    error.value = null
    try {
      // Cancellation optimisation: if a pending CREATE exists for this entity
      // the record was never synced to the server. We can remove everything
      // locally without sending any request — the entity never existed server-side.
      const pendingCreate = await mutationQueue.findPendingCreate('account', id)
      if (pendingCreate && pendingCreate.id != null) {
        await mutationQueue.remove(pendingCreate.id)
        await db.accounts.delete(id)
        accounts.value = accounts.value.filter(a => a.id !== id)
        balances.value.delete(id)
        if (selectedAccountId.value === id) {
          selectedAccountId.value = null
        }
        // Early return — no DELETE mutation needed, nothing to send.
        return
      }

      // Step 1 — Update IndexedDB: set active=false so the record is preserved
      // but marked as archived. _sync_status=pending flags it for sync.
      const localUpdatedAt = new Date().toISOString()
      await db.accounts.update(id, {
        active: false,
        _sync_status: 'pending',
        _local_updated_at: localUpdatedAt
      })

      // Step 2 — Update reactive ref: patch the account in-place so the
      // archivedAccounts computed picks it up and activeAccounts drops it.
      const idx = accounts.value.findIndex(a => a.id === id)
      if (idx !== -1) {
        accounts.value[idx] = {
          ...accounts.value[idx],
          active: false,
          _sync_status: 'pending',
          _local_updated_at: localUpdatedAt
        }
      }

      if (selectedAccountId.value === id) {
        selectedAccountId.value = null
      }

      // Step 3 — Enqueue DELETE mutation. The backend interprets DELETE as a
      // soft-delete (archive), so we use the same 'delete' operation that the
      // original deleteAccount used. No behaviour change on the server side.
      await mutationQueue.enqueue({
        entity_type: 'account',
        entity_id: id,
        operation: 'delete',
        payload: { id }
      })
    } catch (err: any) {
      error.value = err.message || 'Error al archivar cuenta'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Hard-delete an account — permanently removes the record from IndexedDB
   * and enqueues a delete_permanent mutation for the server.
   *
   * Why check transaction/transfer counts before deleting?
   * Hard delete is only allowed when the account has no financial history.
   * The UI disables the button when transactions/transfers exist, but this
   * guard is a belt-and-suspenders check to prevent data corruption if the
   * guard is called programmatically or the UI check is bypassed.
   *
   * Why use delete_permanent operation?
   * The backend distinguishes between soft-delete (DELETE verb → archive) and
   * hard delete (DELETE /accounts/:id/permanent). The 'delete_permanent'
   * operation tells the SyncManager to call the hard-delete endpoint.
   */
  async function hardDeleteAccount(id: string) {
    loading.value = true
    error.value = null
    try {
      // Guard: ensure no transactions reference this account.
      const txCount = await db.transactions.where('account_id').equals(id).count()

      // Guard: ensure no transfers reference this account (either direction).
      // Why two separate counts instead of a combined query?
      // Dexie's .or() on a WhereClause requires both sides to use the same
      // index key. source_account_id and destination_account_id are different
      // fields indexed separately, so two queries and a sum is the idiomatic
      // Dexie approach for an OR across different indexed columns.
      const transferFromCount = await db.transfers.where('source_account_id').equals(id).count()
      const transferToCount = await db.transfers.where('destination_account_id').equals(id).count()

      if (txCount + transferFromCount + transferToCount > 0) {
        throw new Error(
          'Cannot hard-delete an account that has transactions or transfers. Archive it instead.'
        )
      }

      // Step 1 — Remove from IndexedDB entirely.
      await db.accounts.delete(id)

      // Step 2 — Remove from reactive state.
      accounts.value = accounts.value.filter(a => a.id !== id)
      balances.value.delete(id)
      if (selectedAccountId.value === id) {
        selectedAccountId.value = null
      }

      // Step 3 — Enqueue delete_permanent mutation.
      await mutationQueue.enqueue({
        entity_type: 'account',
        entity_id: id,
        operation: 'delete_permanent',
        payload: { id }
      })
    } catch (err: any) {
      error.value = err.message || 'Error al eliminar cuenta permanentemente'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Restore an archived account — flips active back to true and re-enqueues
   * an update mutation so the backend also restores the account.
   *
   * Why use operation 'update' with { active: true }?
   * The backend restore endpoint is a PATCH with active=true. Using the
   * standard 'update' operation keeps the SyncManager logic simple — it
   * already knows how to send PATCH requests for account updates.
   */
  async function restoreAccount(id: string) {
    loading.value = true
    error.value = null
    try {
      const localUpdatedAt = new Date().toISOString()

      // Step 1 — Update IndexedDB: flip active back to true.
      await db.accounts.update(id, {
        active: true,
        _sync_status: 'pending',
        _local_updated_at: localUpdatedAt
      })

      // Step 2 — Update reactive ref: the account moves from archivedAccounts
      // back to activeAccounts via the computed filters.
      const idx = accounts.value.findIndex(a => a.id === id)
      if (idx !== -1) {
        accounts.value[idx] = {
          ...accounts.value[idx],
          active: true,
          _sync_status: 'pending',
          _local_updated_at: localUpdatedAt
        }
      }

      // Step 3 — Enqueue update mutation with { active: true } payload.
      await mutationQueue.enqueue({
        entity_type: 'account',
        entity_id: id,
        operation: 'update',
        payload: { active: true }
      })
    } catch (err: any) {
      error.value = err.message || 'Error al restaurar cuenta'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * deleteAccount — kept as an alias for archiveAccount to avoid breaking
   * any existing callers that have not yet been migrated to the new name.
   *
   * Why an alias instead of a rename everywhere?
   * Component migrations happen in a later task (FE-4). Keeping this alias
   * means the rename does not break callers in the same PR, and the alias
   * can be removed once all callers have been updated.
   */
  const deleteAccount = archiveAccount

  /**
   * Adjust an account's in-memory balance by a signed delta.
   *
   * Called by the transactions and transfers stores immediately after an
   * offline write so the UI reflects the correct balance without waiting
   * for a sync cycle.
   *
   * Why update both balances.value and accounts.value[idx].balance?
   * accountsWithBalances prefers balances.value (kept in memory, updated by
   * adjustBalance on every write and by recomputeBalancesFromTransactions after sync).
   * accounts.value[idx].balance is the cold-start fallback persisted in IndexedDB.
   */
  function adjustBalance(accountId: string, delta: number) {
    // Derive the current balance from whichever source has it.
    // balances.value is populated by adjustBalance() and recomputeBalancesFromTransactions().
    // accounts.value[idx].balance is the fallback from IndexedDB.
    const current = balances.value.get(accountId)
    const account = accounts.value.find(a => a.id === accountId)
    const currentBalance = current?.balance ?? account?.balance ?? 0
    const newBalance = currentBalance + delta

    // Always write to balances.value — even when there was no prior entry.
    // Without this, a cold-start offline session would only update
    // accounts.value[idx].balance. That update gets wiped by refreshFromDB()
    // (triggered after every sync attempt). balances.value survives
    // refreshFromDB() because it only replaces accounts.value, so
    // accountsWithBalances — which prefers balances.value — stays correct.
    balances.value.set(accountId, {
      account_id: accountId,
      balance: newBalance,
      currency: current?.currency ?? account?.currency ?? 'USD'
    })

    // Also update accounts.value[idx].balance so the fallback path and
    // any consumers that read account.balance directly get the fresh value.
    const idx = accounts.value.findIndex(a => a.id === accountId)
    if (idx !== -1) {
      accounts.value[idx] = { ...accounts.value[idx], balance: newBalance }
    }

    // Persist to IndexedDB (fire-and-forget) so the adjusted balance survives
    // a page reload. Without this, reloading resets balance to 0 from the
    // cached list-endpoint data, which never includes accurate balance.
    db.accounts.update(accountId, { balance: newBalance }).catch(() => {})
  }

  function selectAccount(id: string | null) {
    selectedAccountId.value = id
  }

  function getAccountBalance(accountId: string): number {
    // Prefer balances.value (updated by adjustBalance on every write).
    // Fall back to account.balance from accounts.value (persisted in IndexedDB)
    // so the correct value is returned on page reload.
    const fromMap = balances.value.get(accountId)?.balance
    if (fromMap !== undefined) return fromMap
    return accounts.value.find(a => a.id === accountId)?.balance ?? 0
  }

  /**
   * Re-read accounts from IndexedDB without a background API call.
   * Called after wallet:sync-complete to reflect the SyncManager's fresh data.
   */
  async function refreshFromDB() {
    const data = await db.accounts.toArray()
    accounts.value = data.map(normalizeBalance)
  }

  return {
    // State
    accounts,
    balances,
    selectedAccountId,
    loading,
    error,
    // Computed
    activeAccounts,
    archivedAccounts,
    selectedAccount,
    accountsWithBalances,
    // Actions
    fetchAccounts,
    fetchAccountById,
    recomputeBalancesFromTransactions,
    createAccount,
    updateAccount,
    archiveAccount,
    hardDeleteAccount,
    restoreAccount,
    deleteAccount,
    adjustBalance,
    selectAccount,
    getAccountBalance,
    refreshFromDB
  }
})
