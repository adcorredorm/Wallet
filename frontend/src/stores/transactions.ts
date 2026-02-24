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
 * Important: cuenta_id and categoria_id in transaction payloads may be
 * temporary IDs (prefixed 'temp-') if the referenced account or category
 * was created offline. These IDs are preserved as-is in the mutation payload.
 * The SyncManager resolves temp IDs to real server IDs before sending each
 * mutation, walking the queue in FIFO order to guarantee the account CREATE
 * is processed before the transaction CREATE that references it.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { transactionsApi } from '@/api/transactions'
import type {
  CreateTransactionDto,
  UpdateTransactionDto,
  TransactionFilters,
} from '@/types'
import { db, fetchAllWithRevalidation, fetchByIdWithRevalidation, generateTempId, mutationQueue } from '@/offline'
import type { LocalTransaction } from '@/offline'
import { useAccountsStore } from '@/stores/accounts'

// Sort helper: newest transaction first (matches the server's default order).
// Primary: fecha DESC. Secondary: created_at DESC as tiebreaker so that
// transactions created on the same calendar date are ordered newest-first.
// Without the tiebreaker, stable sort would keep IndexedDB insertion order
// (oldest first) among same-date transactions, pushing newly created entries
// below the top-5 slice shown in Recent Activity.
const byFechaDesc = (a: LocalTransaction, b: LocalTransaction) => {
  const byDate = b.fecha.localeCompare(a.fecha)
  if (byDate !== 0) return byDate
  return (b.created_at ?? '').localeCompare(a.created_at ?? '')
}

export const useTransactionsStore = defineStore('transactions', () => {
  // State
  // Why LocalTransaction[] instead of Transaction[]?
  // LocalTransaction extends Transaction, so all consumers continue to work.
  const transactions = ref<LocalTransaction[]>([])
  const filters = ref<TransactionFilters>({})
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Computed
  const incomeTransactions = computed(() =>
    transactions.value.filter(t => t.tipo === 'ingreso')
  )

  const expenseTransactions = computed(() =>
    transactions.value.filter(t => t.tipo === 'gasto')
  )

  const totalIncome = computed(() =>
    incomeTransactions.value.reduce((sum, t) => sum + Number(t.monto), 0)
  )

  const totalExpenses = computed(() =>
    expenseTransactions.value.reduce((sum, t) => sum + Number(t.monto), 0)
  )

  const netBalance = computed(() =>
    totalIncome.value - totalExpenses.value
  )

  // ---------------------------------------------------------------------------
  // Actions — Reads (offline-first, stale-while-revalidate)
  // ---------------------------------------------------------------------------

  async function fetchTransactions(customFilters?: TransactionFilters) {
    loading.value = true
    error.value = null
    try {
      const appliedFilters = customFilters || filters.value

      // Why read ALL local transactions when filters may be set?
      // IndexedDB compound queries for arbitrary filter combinations would
      // require extra indexes and complex Dexie where() chains that mirror the
      // backend filtering logic. For Phase 2, we accept showing the full local
      // cache as the stale value — the network revalidation then replaces it
      // with the correctly filtered server result.
      const localData = await fetchAllWithRevalidation(
        db.transactions,
        () => transactionsApi.getAll(appliedFilters),
        (freshItems) => {
          transactions.value = [...freshItems].sort(byFechaDesc)
        }
      )

      transactions.value = [...localData].sort(byFechaDesc)
    } catch (err: any) {
      error.value = err.message || 'Error al cargar transacciones'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchTransactionById(id: string) {
    loading.value = true
    error.value = null
    try {
      const localItem = await fetchByIdWithRevalidation(
        db.transactions,
        id,
        (txId) => transactionsApi.getById(txId),
        (freshItem) => {
          const index = transactions.value.findIndex(t => t.id === id)
          if (index >= 0) {
            transactions.value[index] = freshItem
          } else {
            transactions.value.push(freshItem)
          }
        }
      )

      if (localItem) {
        const index = transactions.value.findIndex(t => t.id === id)
        if (index >= 0) {
          transactions.value[index] = localItem
        } else {
          transactions.value.push(localItem)
        }
        return localItem
      }
    } catch (err: any) {
      error.value = err.message || 'Error al cargar transacción'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchByAccount(accountId: string, customFilters?: TransactionFilters) {
    loading.value = true
    error.value = null
    try {
      // For account-scoped queries we can do a targeted local read using the
      // cuenta_id index, which is more precise than loading all transactions.
      // However, we still revalidate with the server to pick up changes.
      const localData = await fetchAllWithRevalidation(
        db.transactions,
        () => transactionsApi.getByAccount(accountId, customFilters),
        (freshItems) => {
          // Filter to the requested account before updating the reactive ref so
          // background revalidation doesn't replace account-scoped data with the
          // full merged list (which includes records from other accounts).
          transactions.value = [...freshItems]
            .filter(t => t.cuenta_id === accountId)
            .sort(byFechaDesc)
        }
      )

      // Narrow the local result to the requested account so the stale value
      // shown before revalidation is scoped correctly.
      transactions.value = [...localData]
        .filter(t => t.cuenta_id === accountId)
        .sort(byFechaDesc)
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

    // Build the full local transaction record.
    // tags defaults to an empty array when not provided by the caller, which
    // matches the Transaction interface requirement (tags: string[], not optional).
    // cuenta_id and categoria_id are kept exactly as provided — they may be
    // real server UUIDs or temp-* IDs if the account/category was created
    // offline. The SyncManager resolves temp IDs before the network call.
    const localTransaction: LocalTransaction = {
      id: tempId,
      tipo: data.tipo,
      monto: data.monto,
      fecha: data.fecha,
      cuenta_id: data.cuenta_id,
      categoria_id: data.categoria_id,
      titulo: data.titulo,
      descripcion: data.descripcion,
      tags: data.tags ?? [],
      created_at: now,
      updated_at: now,
      _sync_status: 'pending',
      _local_updated_at: now
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
      const balanceDelta = data.tipo === 'ingreso' ? Number(data.monto) : -Number(data.monto)
      accountsStore.adjustBalance(data.cuenta_id, balanceDelta)

      // Step 3 — Enqueue CREATE mutation.
      // client_id in the payload allows the server to deduplicate retries.
      // cuenta_id / categoria_id are preserved verbatim (may be temp IDs).
      await mutationQueue.enqueue({
        entity_type: 'transaction',
        entity_id: tempId,
        operation: 'create',
        payload: { ...data, client_id: tempId }
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

    loading.value = true
    error.value = null
    try {
      // Step 1 — Partial IndexedDB update.
      await db.transactions.update(id, {
        ...data,
        _sync_status: 'pending',
        _local_updated_at: localUpdatedAt
      })

      // Step 2 — Reactive ref update + optimistic balance adjustment.
      const idx = transactions.value.findIndex(t => t.id === id)
      if (idx !== -1) {
        const old = transactions.value[idx]
        transactions.value[idx] = {
          ...old,
          ...data,
          _sync_status: 'pending',
          _local_updated_at: localUpdatedAt
        }

        // Compute how this update changes the account balance.
        // If cuenta_id changed, reverse the old account's effect and apply
        // the new amount to the new account. If it stayed the same, just
        // apply the net difference.
        const accountsStore = useAccountsStore()
        const oldImpact = old.tipo === 'ingreso' ? Number(old.monto) : -Number(old.monto)
        const newTipo = data.tipo ?? old.tipo
        const newMonto = data.monto ?? old.monto
        const newCuentaId = data.cuenta_id ?? old.cuenta_id
        const newImpact = newTipo === 'ingreso' ? Number(newMonto) : -Number(newMonto)
        if (newCuentaId === old.cuenta_id) {
          accountsStore.adjustBalance(old.cuenta_id, newImpact - oldImpact)
        } else {
          accountsStore.adjustBalance(old.cuenta_id, -oldImpact)
          accountsStore.adjustBalance(newCuentaId, newImpact)
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
          payload: data as Record<string, unknown>
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
          const delta = tx.tipo === 'ingreso' ? -Number(tx.monto) : Number(tx.monto)
          accountsStore.adjustBalance(tx.cuenta_id, delta)
        }
        return
      }

      // Entity exists on the server — mark pending, remove from UI, enqueue DELETE.
      await db.transactions.update(id, { _sync_status: 'pending' })
      transactions.value = transactions.value.filter(t => t.id !== id)
      if (tx) {
        const accountsStore = useAccountsStore()
        const delta = tx.tipo === 'ingreso' ? -Number(tx.monto) : Number(tx.monto)
        accountsStore.adjustBalance(tx.cuenta_id, delta)
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
    return transactions.value.filter(t => t.cuenta_id === accountId)
  }

  function getTransactionsByCategory(categoryId: string): LocalTransaction[] {
    return transactions.value.filter(t => t.categoria_id === categoryId)
  }

  /**
   * Re-read the transactions table from IndexedDB without triggering a
   * background API call. Called after wallet:sync-complete to update the
   * reactive state from the fresh data that the SyncManager just wrote.
   */
  async function refreshFromDB() {
    const data = await db.transactions.toArray()
    transactions.value = [...data].sort(byFechaDesc)
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
