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
import { db, generateTempId } from '@/offline'
import type { LocalTransaction } from '@/offline'
import { useAccountsStore } from '@/stores/accounts'
import { useExchangeRatesStore } from '@/stores/exchangeRates'
import { useSettingsStore } from '@/stores/settings'
import { useOfflineMutation } from '@/composables/useOfflineMutation'

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

  // ---------------------------------------------------------------------------
  // Offline mutation composable — transactions
  // ---------------------------------------------------------------------------

  const transactionMutation = useOfflineMutation<LocalTransaction, CreateTransactionDto, UpdateTransactionDto>({
    entityType: 'transaction',
    table: db.transactions,
    items: transactions,
    generateId: generateTempId,
    toLocal: (dto, id, now) => {
      const txAccount = accountsStore.accounts.find(a => a.id === dto.account_id)
      const txRate = txAccount
        ? exchangeRatesStore.getRate(txAccount.currency, settingsStore.primaryCurrency)
        : null

      return {
        id,
        type: dto.type,
        amount: dto.amount,
        date: dto.date,
        account_id: dto.account_id,
        category_id: dto.category_id,
        title: dto.title,
        description: dto.description,
        tags: dto.tags ?? [],
        created_at: now,
        updated_at: now,
        _sync_status: 'pending' as const,
        _local_updated_at: now,
        base_rate: txRate,
      }
    },
    mergeUpdate: (existing, dto, _now) => ({
      ...existing,
      ...dto,
    } as LocalTransaction),
    toCreatePayload: (local) => ({
      type: local.type,
      amount: local.amount,
      date: local.date,
      account_id: local.account_id,
      category_id: local.category_id,
      title: local.title,
      description: local.description,
      tags: local.tags,
      base_rate: local.base_rate,
      offline_id: local.id,
    }),
    toUpdatePayload: (dto) => dto as Record<string, unknown>,
    afterCreate: (local) => {
      const delta = local.type === 'income' ? Number(local.amount) : -Number(local.amount)
      accountsStore.adjustBalance(local.account_id, delta)
    },
    beforeUpdate: (_id, dto, existing) => {
      const effectiveAccountId = dto.account_id ?? existing.account_id
      const updateAccount = effectiveAccountId
        ? accountsStore.accounts.find(a => a.id === effectiveAccountId)
        : undefined
      const updateRate = updateAccount
        ? exchangeRatesStore.getRate(updateAccount.currency, settingsStore.primaryCurrency)
        : null
      return { ...dto, base_rate: updateRate } as UpdateTransactionDto
    },
    afterUpdate: (_id, _dto, old, merged) => {
      const oldImpact = old.type === 'income' ? Number(old.amount) : -Number(old.amount)
      const newType = merged.type
      const newAmount = merged.amount
      const newAccountId = merged.account_id
      const newImpact = newType === 'income' ? Number(newAmount) : -Number(newAmount)
      if (newAccountId === old.account_id) {
        accountsStore.adjustBalance(old.account_id, newImpact - oldImpact)
      } else {
        accountsStore.adjustBalance(old.account_id, -oldImpact)
        accountsStore.adjustBalance(newAccountId, newImpact)
      }
    },
    afterRemove: (_id, removed) => {
      const delta = removed.type === 'income' ? -Number(removed.amount) : Number(removed.amount)
      accountsStore.adjustBalance(removed.account_id, delta)
    },
    afterRemoveEvent: 'wallet:local-delete',
  })

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
    loading.value = true
    error.value = null
    try {
      const local = await transactionMutation.create(data)
      // Move to front for display order (composable pushes to end)
      const idx = transactions.value.indexOf(local)
      if (idx > 0) {
        transactions.value.splice(idx, 1)
        transactions.value.unshift(local)
      }
      return local
    } catch (err: any) {
      error.value = err.message || 'Error al crear transaccion'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateTransaction(id: string, data: UpdateTransactionDto) {
    loading.value = true
    error.value = null
    try {
      await transactionMutation.update(id, data)
    } catch (err: any) {
      error.value = err.message || 'Error al actualizar transaccion'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteTransaction(id: string) {
    loading.value = true
    error.value = null
    try {
      await transactionMutation.remove(id)
    } catch (err: any) {
      error.value = err.message || 'Error al eliminar transaccion'
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
