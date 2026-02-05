/**
 * Transactions Store
 *
 * Manages income and expense transactions
 * - Filtering by account, category, date range, type
 * - Pagination support
 * - CRUD operations
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { transactionsApi } from '@/api/transactions'
import type {
  Transaction,
  CreateTransactionDto,
  UpdateTransactionDto,
  TransactionFilters,
  TransactionType
} from '@/types'

export const useTransactionsStore = defineStore('transactions', () => {
  // State
  const transactions = ref<Transaction[]>([])
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

  // Actions
  async function fetchTransactions(customFilters?: TransactionFilters) {
    loading.value = true
    error.value = null
    try {
      const appliedFilters = customFilters || filters.value
      transactions.value = await transactionsApi.getAll(appliedFilters)
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
      const transaction = await transactionsApi.getById(id)
      // Update or add to transactions array
      const index = transactions.value.findIndex(t => t.id === id)
      if (index >= 0) {
        transactions.value[index] = transaction
      } else {
        transactions.value.push(transaction)
      }
      return transaction
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
      transactions.value = await transactionsApi.getByAccount(accountId, customFilters)
    } catch (err: any) {
      error.value = err.message || 'Error al cargar transacciones de la cuenta'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createTransaction(data: CreateTransactionDto) {
    loading.value = true
    error.value = null
    try {
      const newTransaction = await transactionsApi.create(data)
      transactions.value.unshift(newTransaction) // Add to beginning
      return newTransaction
    } catch (err: any) {
      error.value = err.message || 'Error al crear transacción'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateTransaction(id: string, data: UpdateTransactionDto) {
    loading.value = true
    error.value = null
    try {
      const updatedTransaction = await transactionsApi.update(id, data)
      const index = transactions.value.findIndex(t => t.id === id)
      if (index >= 0) {
        transactions.value[index] = updatedTransaction
      }
      return updatedTransaction
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
      await transactionsApi.delete(id)
      transactions.value = transactions.value.filter(t => t.id !== id)
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

  function getTransactionsByAccount(accountId: string): Transaction[] {
    return transactions.value.filter(t => t.cuenta_id === accountId)
  }

  function getTransactionsByCategory(categoryId: string): Transaction[] {
    return transactions.value.filter(t => t.categoria_id === categoryId)
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
    getTransactionsByCategory
  }
})
