<script setup lang="ts">
/**
 * Accounts List View
 *
 * Shows all user accounts with balances
 */

import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAccountsStore, useUiStore } from '@/stores'
import AccountList from '@/components/accounts/AccountList.vue'
import SimpleFab from '@/components/ui/SimpleFab.vue'

const router = useRouter()
const accountsStore = useAccountsStore()
const uiStore = useUiStore()

const accounts = computed(() => accountsStore.accounts)
const balances = computed(() => {
  const map = new Map<string, number>()
  accountsStore.accounts.forEach(account => {
    map.set(account.id, accountsStore.getAccountBalance(account.id))
  })
  return map
})

onMounted(async () => {
  try {
    await accountsStore.fetchAccounts()
    // Fetch balances for all accounts
    await accountsStore.fetchAllBalances()
  } catch (error: any) {
    uiStore.showError(error.message || 'Error al cargar cuentas')
  }
})

function goToAccount(account: any) {
  router.push(`/accounts/${account.id}`)
}

function createAccount() {
  router.push('/accounts/new')
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div>
      <h1 class="text-2xl font-bold">Cuentas</h1>
    </div>

    <!-- Account list -->
    <AccountList
      :accounts="accounts"
      :balances="balances"
      :loading="accountsStore.loading"
      @account-click="goToAccount"
      @create-click="createAccount"
    />

    <!-- Floating Action Button -->
    <SimpleFab
      aria-label="Crear nueva cuenta"
      @click="createAccount"
    />
  </div>
</template>
