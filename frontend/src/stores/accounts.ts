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
 * - Account balances (fetched from backend)
 * - CRUD operations for accounts
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { accountsApi } from '@/api/accounts'
import type { Account, CreateAccountDto, UpdateAccountDto, AccountBalance } from '@/types'

export const useAccountsStore = defineStore('accounts', () => {
  // State
  const accounts = ref<Account[]>([])
  const balances = ref<Map<string, AccountBalance>>(new Map())
  const selectedAccountId = ref<string | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Computed
  const activeAccounts = computed(() =>
    accounts.value.filter(account => account.activa)
  )

  const selectedAccount = computed(() =>
    accounts.value.find(account => account.id === selectedAccountId.value) || null
  )

  const accountsWithBalances = computed(() =>
    accounts.value.map(account => ({
      ...account,
      // Use balance from account object (already included in API response)
      // Fall back to balances map if not present
      balance: typeof account.balance === 'number'
        ? account.balance
        : (balances.value.get(account.id)?.balance || 0)
    }))
  )

  // Actions
  async function fetchAccounts(activeOnly = false) {
    loading.value = true
    error.value = null
    try {
      const fetchedAccounts = await accountsApi.getAll(activeOnly ? true : undefined)
      // Convert balance string to number if present
      accounts.value = fetchedAccounts.map((account: any) => ({
        ...account,
        balance: account.balance ? Number(account.balance) : 0
      }))
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
      const account = await accountsApi.getById(id)
      // Update or add to accounts array
      const index = accounts.value.findIndex(a => a.id === id)
      if (index >= 0) {
        accounts.value[index] = account
      } else {
        accounts.value.push(account)
      }
      // Fetch balance for this account
      await fetchBalance(id)
      return account
    } catch (err: any) {
      error.value = err.message || 'Error al cargar cuenta'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchBalance(accountId: string) {
    try {
      const balance = await accountsApi.getBalance(accountId)
      balances.value.set(accountId, balance)
    } catch (err: any) {
      console.error('Error fetching balance:', err)
    }
  }

  async function fetchAllBalances() {
    const promises = accounts.value.map(account => fetchBalance(account.id))
    await Promise.all(promises)
  }

  async function createAccount(data: CreateAccountDto) {
    loading.value = true
    error.value = null
    try {
      const newAccount = await accountsApi.create(data)
      accounts.value.push(newAccount)
      // Initialize balance to 0
      balances.value.set(newAccount.id, {
        account_id: newAccount.id,
        balance: 0,
        currency: newAccount.divisa
      })
      return newAccount
    } catch (err: any) {
      error.value = err.message || 'Error al crear cuenta'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateAccount(id: string, data: UpdateAccountDto) {
    loading.value = true
    error.value = null
    try {
      const updatedAccount = await accountsApi.update(id, data)
      const index = accounts.value.findIndex(a => a.id === id)
      if (index >= 0) {
        accounts.value[index] = updatedAccount
      }
      return updatedAccount
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
      await accountsApi.delete(id)
      accounts.value = accounts.value.filter(a => a.id !== id)
      balances.value.delete(id)
      if (selectedAccountId.value === id) {
        selectedAccountId.value = null
      }
    } catch (err: any) {
      error.value = err.message || 'Error al eliminar cuenta'
      throw err
    } finally {
      loading.value = false
    }
  }

  function selectAccount(id: string | null) {
    selectedAccountId.value = id
  }

  function getAccountBalance(accountId: string): number {
    return balances.value.get(accountId)?.balance || 0
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
    fetchBalance,
    fetchAllBalances,
    createAccount,
    updateAccount,
    deleteAccount,
    selectAccount,
    getAccountBalance
  }
})
