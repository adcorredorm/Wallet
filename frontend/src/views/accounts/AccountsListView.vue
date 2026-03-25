<script setup lang="ts">
/**
 * Accounts List View
 *
 * Shows all user accounts with balances.
 * Provides a "Mostrar archivadas" toggle so the user can optionally
 * include archived accounts in the list.
 */

import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAccountsStore, useUiStore } from '@/stores'
import AccountList from '@/components/accounts/AccountList.vue'
import SimpleFab from '@/components/ui/SimpleFab.vue'

const router = useRouter()
const accountsStore = useAccountsStore()
const uiStore = useUiStore()

/** When true, archived accounts are appended after the active ones. */
const showArchived = ref<boolean>(false)

/**
 * The set of accounts to render.
 * Active accounts are always shown first; archived accounts are appended
 * when the user enables the toggle.
 */
const displayedAccounts = computed(() =>
  showArchived.value
    ? [...accountsStore.activeAccounts, ...accountsStore.archivedAccounts]
    : accountsStore.activeAccounts
)

const balances = computed(() => {
  const map = new Map<string, number>()
  displayedAccounts.value.forEach(account => {
    map.set(account.id, accountsStore.getAccountBalance(account.id))
  })
  return map
})

onMounted(async () => {
  try {
    // Loads IndexedDB immediately; background revalidation updates the list.
    await accountsStore.fetchAccounts()
  } catch (error: any) {
    uiStore.showError(error.message || 'Error al cargar cuentas')
  }
  // Balance is kept accurate by adjustBalance() on every write (persisted to
  // IndexedDB). After sync, recomputeBalancesFromTransactions() updates it
  // from the full local transaction history. No backend balance call needed.
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
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold">Cuentas</h1>

      <!-- Mostrar archivadas toggle — only shown when there are archived accounts -->
      <button
        v-if="accountsStore.archivedAccounts.length > 0"
        class="flex items-center gap-2 text-sm px-3 py-2 rounded-lg transition-colors min-h-[44px]"
        :class="showArchived
          ? 'bg-blue-600/20 text-blue-400 border border-blue-600/30'
          : 'bg-dark-bg-secondary text-dark-text-secondary border border-dark-bg-tertiary/50 hover:bg-dark-bg-tertiary/50'"
        :aria-pressed="showArchived"
        aria-label="Mostrar cuentas archivadas"
        @click="showArchived = !showArchived"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8l1 12a2 2 0 002 2h8a2 2 0 002-2L19 8M10 12v4m4-4v4" />
        </svg>
        Mostrar archivadas
      </button>
    </div>

    <!-- Account list -->
    <AccountList
      :accounts="displayedAccounts"
      :balances="balances"
      :loading="accountsStore.loading"
      @account-click="goToAccount"
      @create-click="createAccount"
    />

    <!-- Floating Action Button -->
    <SimpleFab
      ariaLabel="Crear nueva cuenta"
      @click="createAccount"
    />
  </div>
</template>
