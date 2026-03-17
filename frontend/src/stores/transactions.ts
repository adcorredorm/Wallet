/**
 * Transactions Store
 *
 * Manages income and expense transactions
 * - Filtering by account, category, date range, type
 * - Pagination support
 * - CRUD operations
 *
 * Phase 3 change: write actions now follow the offline-first pattern.
 * Writes go to IndexedDB and the mutation queue immediately; the UI updates
 * optimistically. The SyncManager (Phase 4) will flush to the server when
 * connectivity is available.
 *
 * Important: account_id and category_id in transaction payloads may be
 * temporary IDs (prefixed 'temp-') if the referenced account or category
 * was created offline. These IDs are preserved as-is in the mutation payload.
 * The SyncManager resolves temp IDs to real server IDs before sending each
 * mutation, walking the queue in FIFO order to guarantee the account CREATE
 * is processed before the transaction CREATE that references it.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  CreateTransactionDto,
  UpdateTransactionDto,
  TransactionFilters,
} from '@/types'
import { db, generateTempId, mutationQueue } from '@/offline'
import type { LocalTransaction } from '@/offline'
import { useAccountsStore } from '@/stores/accounts'
import { useExchangeRatesStore } from '@/stores/exchangeRates'
import { useSettingsStore } from '@/stores/settings'

// Sort helper: newest transaction first (matches the server's default order).
// Primary: date DESC. Secondary: created_at DESC as tiebreaker so that
// transactions created on the same calendar date are ordered newest-first.
// Without the tiebreaker, stable sort would keep IndexedDB insertion order
// (oldest first) among same-date transactions, pushing newly created entries
// below the top-5 slice shown in Recent Activity.
const byDateDesc = (a: LocalTransaction, b: LocalTransaction) => {
  const byDate = b.date.localeCompare(a.date)
  if (byDate !== 0) return byDate
  return (b.created_at ?? '').localeCompare(a.created_at ?? '')
}

export const useTransactionsStore = defineStore('transactions', () => {
  // Cross-store references — called at the top of the setup function per the
  // Pinia setup-store pattern. Vue tracks reactive reads from these stores
  // inside computed() bodies automatically, so the converted totals below
  // re-compute whenever rates, settings, or accounts change.
  const accountsStore = useAccountsStore()
  const exchangeRatesStore = useExchangeRatesStore()
  const settingsStore = useSettingsStore()

  // State
  // Why LocalTransaction[] instead of Transaction[]?
  // LocalTransaction extends Transaction, so all consumers continue to work.
  const transactions = ref<LocalTransaction[]>([])
  const filters = ref<TransactionFilters>({})
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Computed
  const incomeTransactions = computed(() =>
    transactions.value.filter(t => t.type === 'income')
  )

  const expenseTransactions = computed(() =>
    transactions.value.filter(t => t.type === 'expense')
  )

  const totalIncome = computed(() =>
    incomeTransactions.value.reduce((sum, t) => sum + Number(t.amount), 0)
  )

  const totalExpenses = computed(() =>
    expenseTransactions.value.reduce((sum, t) => sum + Number(t.amount), 0)
  )

  const netBalance = computed(() =>
    totalIncome.value - totalExpenses.value
  )

  // ---------------------------------------------------------------------------
  // Dashboard totals — converted to the user's primary currency
  //
  // Why add *Converted variants instead of changing the existing computeds?
  // The existing totalIncome/totalExpenses/netBalance are used by the account
  // detail view where filters.account_id is set and all transactions share the
  // same currency. That single-currency sum is correct and must not change.
  //
  // These new variants are for the dashboard: they convert each transaction's
  // amount to primaryCurrency via the exchange rates store before summing,
  // avoiding the meaningless cross-currency total (e.g. 100 USD + 500,000 COP).
  //
  // Graceful degradation: exchangeRatesStore.convert() returns the original
  // amount unchanged when a currency is not yet cached (e.g. first offline
  // start before any rate fetch). This means the sum is best-effort rather
  // than NaN or 0, so the dashboard is still useful with partial rate data.
  //
  // Reactivity: Vue tracks all reactive reads inside computed() — including
  // reads of accountsStore.accounts, exchangeRatesStore.rates, and
  // settingsStore.settings — so these recompute automatically when any of
  // those change (rates fetched, user changes primaryCurrency, etc.).
  // ---------------------------------------------------------------------------

  const totalIncomeConverted = computed(() =>
    incomeTransactions.value.reduce((sum, tx) => {
      const account = accountsStore.accounts.find(a => a.id === tx.account_id)
      if (!account) return sum
      return sum + exchangeRatesStore.convert(
        Number(tx.amount),
        account.currency,
        settingsStore.primaryCurrency
      )
    }, 0)
  )

  const totalExpensesConverted = computed(() =>
    expenseTransactions.value.reduce((sum, tx) => {
      const account = accountsStore.accounts.find(a => a.id === tx.account_id)
      if (!account) return sum
      return sum + exchangeRatesStore.convert(
        Number(tx.amount),
        account.currency,
        settingsStore.primaryCurrency
      )
    }, 0)
  )

  const netBalanceConverted = computed(() =>
    totalIncomeConverted.value - totalExpensesConverted.value
  )

  // ---------------------------------------------------------------------------
  // Actions — Reads (offline-first, Dexie-only)
  // ---------------------------------------------------------------------------

  async function fetchTransactions() {
    loading.value = true
    error.value = null
    try {
      await refreshFromDB()
    } catch (err: any) {
      error.value = err.message || 'Error al cargar transacciones'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchTransactionById(id: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const item = await db.transactions.get(id)
      if (item) {
        const index = transactions.value.findIndex(t => t.id === id)
        if (index >= 0) transactions.value[index] = item
        else transactions.value.push(item)
      }
    } catch (err: any) {
      error.value = err.message || 'Error al cargar transacción'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchByAccount(accountId: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const data = await db.transactions
        .where('account_id').equals(accountId)
        .toArray()
      transactions.value = [...data].sort(byDateDesc)
    } catch (err: any) {
      error.value = err.message || 'Error al cargar transacciones de la cuenta'
      throw err
    } finally {
      loading.value = false
    }
  }

  // ---------------------------------------------------------------------------
  // Actions — Writes (Phase 3: offline-first pattern)
  // ---------------------------------------------------------------------------

  async function createTransaction(data: CreateTransactionDto) {
    const tempId = generateTempId()
    const now = new Date().toISOString()

    // Compute base_rate: how many primaryCurrency units equal 1 unit of this
    // account's currency at the moment of creation. null when offline with no cache.
    const txAccount = accountsStore.accounts.find(a => a.id === data.account_id)
    const txRate = txAccount
      ? exchangeRatesStore.getRate(txAccount.currency, settingsStore.primaryCurrency)
      : null

    // Build the full local transaction record.
    // tags defaults to an empty array when not provided by the caller, which
    // matches the Transaction interface requirement (tags: string[], not optional).
    // account_id and category_id are kept exactly as provided — they may be
    // real server UUIDs or temp-* IDs if the account/category was created
    // offline. The SyncManager resolves temp IDs before the network call.
    const localTransaction: LocalTransaction = {
      id: tempId,
      type: data.type,
      amount: data.amount,
      date: data.date,
      account_id: data.account_id,
      category_id: data.category_id,
      title: data.title,
      description: data.description,
      tags: data.tags ?? [],
      created_at: now,
      updated_at: now,
      _sync_status: 'pending',
      _local_updated_at: now,
      base_rate: txRate
    }

    loading.value = true
    error.value = null
    try {
      // Step 1 — IndexedDB write.
      await db.transactions.add(localTransaction)

      // Step 2 — Optimistic UI update.
      // unshift keeps the most recent transaction at the top of the list,
      // matching the display order used by the existing read actions.
      transactions.value.unshift(localTransaction)

      // Adjust the account's in-memory balance immediately so balance
      // displays are accurate while offline (before server sync).
      const accountsStore = useAccountsStore()
      const balanceDelta = data.type === 'income' ? Number(data.amount) : -Number(data.amount)
      accountsStore.adjustBalance(data.account_id, balanceDelta)

      // Step 3 — Enqueue CREATE mutation.
      // offline_id in the payload allows the server to deduplicate retries.
      // account_id / category_id are preserved verbatim (may be temp IDs).
      await mutationQueue.enqueue({
        entity_type: 'transaction',
        entity_id: tempId,
        operation: 'create',
        payload: { ...data, base_rate: txRate, offline_id: tempId }
      })

      return localTransaction
    } catch (err: any) {
      error.value = err.message || 'Error al crear transacción'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateTransaction(id: string, data: UpdateTransactionDto) {
    const localUpdatedAt = new Date().toISOString()

    // Recompute base_rate using the effective account after this update.
    const effectiveAccountId = data.account_id ?? (
      transactions.value.find(t => t.id === id)?.account_id
    )
    const updateAccount = effectiveAccountId
      ? accountsStore.accounts.find(a => a.id === effectiveAccountId)
      : undefined
    const updateRate = updateAccount
      ? exchangeRatesStore.getRate(updateAccount.currency, settingsStore.primaryCurrency)
      : null

    loading.value = true
    error.value = null
    try {
      // Step 1 — Partial IndexedDB update.
      await db.transactions.update(id, {
        ...data,
        base_rate: updateRate,
        _sync_status: 'pending',
        _local_updated_at: localUpdatedAt
      } as Parameters<typeof db.transactions.update>[1])

      // Step 2 — Reactive ref update + optimistic balance adjustment.
      const idx = transactions.value.findIndex(t => t.id === id)
      if (idx !== -1) {
        const old = transactions.value[idx]
        transactions.value[idx] = {
          ...old,
          ...data,
          base_rate: updateRate,
          _sync_status: 'pending',
          _local_updated_at: localUpdatedAt
        } as LocalTransaction

        // Compute how this update changes the account balance.
        // If account_id changed, reverse the old account's effect and apply
        // the new amount to the new account. If it stayed the same, just
        // apply the net difference.
        const accountsStore = useAccountsStore()
        const oldImpact = old.type === 'income' ? Number(old.amount) : -Number(old.amount)
        const newType = data.type ?? old.type
        const newAmount = data.amount ?? old.amount
        const newAccountId = data.account_id ?? old.account_id
        const newImpact = newType === 'income' ? Number(newAmount) : -Number(newAmount)
        if (newAccountId === old.account_id) {
          accountsStore.adjustBalance(old.account_id, newImpact - oldImpact)
        } else {
          accountsStore.adjustBalance(old.account_id, -oldImpact)
          accountsStore.adjustBalance(newAccountId, newImpact)
        }
      }

      // Step 3 — Merge optimisation: collapse UPDATE into pending CREATE if
      // the transaction hasn't been synced yet.
      const pendingCreate = await mutationQueue.findPendingCreate('transaction', id)
      if (pendingCreate && pendingCreate.id != null) {
        await mutationQueue.updatePayload(pendingCreate.id, {
          ...pendingCreate.payload,
          ...data
        })
      } else {
        await mutationQueue.enqueue({
          entity_type: 'transaction',
          entity_id: id,
          operation: 'update',
          payload: { ...data, base_rate: updateRate } as Record<string, unknown>
        })
      }
    } catch (err: any) {
      error.value = err.message || 'Error al actualizar transacción'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteTransaction(id: string) {
    loading.value = true
    error.value = null
    try {
      // Capture the transaction before removal so we can reverse its balance effect.
      const tx = transactions.value.find(t => t.id === id)

      // Cancellation optimisation: if the CREATE is still queued (never synced),
      // cancel both the CREATE and the entity — nothing to send to the server.
      const pendingCreate = await mutationQueue.findPendingCreate('transaction', id)
      if (pendingCreate && pendingCreate.id != null) {
        await mutationQueue.remove(pendingCreate.id)
        await db.transactions.delete(id)
        transactions.value = transactions.value.filter(t => t.id !== id)
        if (tx) {
          const accountsStore = useAccountsStore()
          const delta = tx.type === 'income' ? -Number(tx.amount) : Number(tx.amount)
          accountsStore.adjustBalance(tx.account_id, delta)
        }
        return
      }

      // Entity exists on the server — hard-delete from Dexie, remove from UI, enqueue DELETE.
      // Hard-delete (not mark-pending) so usePaginatedList never shows the item again.
      // The mutation queue handles server sync; markError in SyncManager is a no-op on
      // a missing record, and the server DELETE is still sent regardless.
      await db.transactions.delete(id)
      transactions.value = transactions.value.filter(t => t.id !== id)
      if (tx) {
        const accountsStore = useAccountsStore()
        const delta = tx.type === 'income' ? -Number(tx.amount) : Number(tx.amount)
        accountsStore.adjustBalance(tx.account_id, delta)
      }

      await mutationQueue.enqueue({
        entity_type: 'transaction',
        entity_id: id,
        operation: 'delete',
        payload: { id }
      })
    } catch (err: any) {
      error.value = err.message || 'Error al eliminar transacción'
      throw err
    } finally {
      loading.value = false
    }
  }

  function setFilters(newFilters: TransactionFilters) {
    filters.value = newFilters
  }

  function clearFilters() {
    filters.value = {}
  }

  function getTransactionsByAccount(accountId: string): LocalTransaction[] {
    return transactions.value.filter(t => t.account_id === accountId)
  }

  function getTransactionsByCategory(categoryId: string): LocalTransaction[] {
    return transactions.value.filter(t => t.category_id === categoryId)
  }

  /**
   * Re-read the transactions table from IndexedDB without triggering a
   * background API call. Called after wallet:sync-complete to update the
   * reactive state from the fresh data that the SyncManager just wrote.
   */
  async function refreshFromDB() {
    const data = await db.transactions.toArray()
    transactions.value = [...data].sort(byDateDesc)
  }

  return {
    // State
    transactions,
    filters,
    loading,
    error,
    // Computed
    incomeTransactions,
    expenseTransactions,
    totalIncome,
    totalExpenses,
    netBalance,
    totalIncomeConverted,
    totalExpensesConverted,
    netBalanceConverted,
    // Actions
    fetchTransactions,
    fetchTransactionById,
    fetchByAccount,
    createTransaction,
    updateTransaction,
    deleteTransaction,
    setFilters,
    clearFilters,
    getTransactionsByAccount,
    getTransactionsByCategory,
    refreshFromDB
  }
})
