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
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { accountsApi } from '@/api/accounts'
import type { CreateAccountDto, UpdateAccountDto, AccountBalance } from '@/types'
import { db, fetchAllWithRevalidation, fetchByIdWithRevalidation, generateTempId, mutationQueue } from '@/offline'
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

  async function fetchAccounts(activeOnly = false) {
    loading.value = true
    error.value = null
    try {
      // fetchAllWithRevalidation:
      //   1. Returns cached IndexedDB data immediately (fast path).
      //   2. If online, revalidates with the API in the background.
      //   3. Calls onFreshData callback with the updated array from the server.
      //
      // Why pass the API fetcher as an arrow function?
      // accountsApi.getAll() accepts an optional `activeOnly` argument. We
      // capture that argument in the closure so the repository doesn't need to
      // know about it.
      const localData = await fetchAllWithRevalidation(
        db.accounts,
        () => accountsApi.getAll(activeOnly ? true : undefined).then(
          (items) => items.map((item: any) => ({
            ...item,
            balance: item.balance ? Number(item.balance) : 0
          }))
        ),
        (freshItems) => {
          // This callback fires after background network revalidation succeeds.
          // freshItems came from IndexedDB after bulkPut — the bulkPut may have
          // overwritten the locally-correct balance with the server's stale value
          // (the list endpoint balance excludes pending offline transactions).
          //
          // Restore the correct balance from:
          //   1. balances.value — set by adjustBalance() in this session
          //   2. accounts.value — loaded from IndexedDB at the start of fetchAccounts
          //      (has the value persisted by the most recent adjustBalance() call,
          //      which was written to IndexedDB BEFORE bulkPut ran)
          //
          // Also repair IndexedDB so the next page reload shows the right balance.
          accounts.value = freshItems.map(item => {
            const normalized = normalizeBalance(item)
            const localBalance = balances.value.get(item.id)?.balance
                               ?? accounts.value.find(a => a.id === item.id)?.balance
            if (localBalance !== undefined) {
              db.accounts.update(item.id, { balance: localBalance }).catch(() => {})
              return { ...normalized, balance: localBalance }
            }
            return normalized
          })
        }
      )

      // Populate the store with whatever came back (local cache or first-load
      // network data). normalizeBalance ensures balance is always a number.
      accounts.value = localData.map(normalizeBalance)
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

  async function deleteAccount(id: string) {
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

      // The entity exists on the server. Update sync status so the UI can
      // show a "pending deletion" indicator if needed, remove from the
      // reactive list optimistically, then enqueue the DELETE.
      await db.accounts.update(id, { _sync_status: 'pending' })
      accounts.value = accounts.value.filter(a => a.id !== id)
      balances.value.delete(id)
      if (selectedAccountId.value === id) {
        selectedAccountId.value = null
      }

      await mutationQueue.enqueue({
        entity_type: 'account',
        entity_id: id,
        operation: 'delete',
        payload: { id }
      })
    } catch (err: any) {
      error.value = err.message || 'Error al eliminar cuenta'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Adjust an account's in-memory balance by a signed delta.
   *
   * Called by the transactions and transfers stores immediately after an
   * offline write so the UI reflects the correct balance without waiting
   * for a server round-trip or a /balance API call.
   *
   * Why update both balances.value and accounts.value[idx].balance?
   * accountsWithBalances prefers balances.value (from the /balance endpoint).
   * accounts.value[idx].balance is the cold-start fallback when no /balance
   * fetch has run yet for a given account.
   */
  function adjustBalance(accountId: string, delta: number) {
    // Derive the current balance from whichever source has it.
    // balances.value is populated by the /balance endpoint (authoritative).
    // accounts.value[idx].balance is the fallback from IndexedDB / list endpoint.
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
    selectedAccount,
    accountsWithBalances,
    // Actions
    fetchAccounts,
    fetchAccountById,
    recomputeBalancesFromTransactions,
    createAccount,
    updateAccount,
    deleteAccount,
    adjustBalance,
    selectAccount,
    getAccountBalance,
    refreshFromDB
  }
})
