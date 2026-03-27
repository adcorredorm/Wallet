<script setup lang="ts">
/**
 * Accounts List View
 *
 * Shows all user accounts with balances.
 * Provides a "Mostrar archivadas" toggle and a "Reordenar" toggle.
 * In reorder mode: drag handles appear, card navigation is disabled,
 * "Listo" exits the mode.
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

/** When true, active accounts render with drag handles and drag-and-drop is enabled. */
const reorderMode = ref<boolean>(false)

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

/** Only show reorder button when there are 2+ active accounts. */
const canReorder = computed(() => accountsStore.activeAccounts.length >= 2)

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

async function handleReorder(orderedIds: string[]) {
  try {
    await accountsStore.reorderAccounts(orderedIds)
  } catch (error: any) {
    uiStore.showError(error.message || 'Error al reordenar cuentas')
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between gap-2 flex-wrap">
      <h1 class="text-2xl font-bold">Cuentas</h1>

      <div class="flex items-center gap-2">
        <!-- Reordenar / Listo toggle — only shown when there are 2+ active accounts -->
        <button
          v-if="canReorder"
          class="flex items-center gap-2 text-sm px-3 py-2 rounded-lg transition-colors min-h-[44px]"
          :class="reorderMode
            ? 'bg-green-600/20 text-green-400 border border-green-600/30'
            : 'bg-dark-bg-secondary text-dark-text-secondary border border-dark-bg-tertiary/50 hover:bg-dark-bg-tertiary/50'"
          :aria-pressed="reorderMode"
          :aria-label="reorderMode ? 'Salir del modo reordenar' : 'Reordenar cuentas'"
          @click="reorderMode = !reorderMode"
        >
          <svg v-if="!reorderMode" xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
          {{ reorderMode ? 'Listo' : 'Reordenar' }}
        </button>

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
    </div>

    <!-- Account list -->
    <AccountList
      :accounts="displayedAccounts"
      :balances="balances"
      :loading="accountsStore.loading"
      :reorder-mode="reorderMode"
      @account-click="goToAccount"
      @create-click="createAccount"
      @reorder="handleReorder"
    />

    <!-- FAB hidden in reorder mode to avoid accidental navigation -->
    <SimpleFab
      v-if="!reorderMode"
      ariaLabel="Crear nueva cuenta"
      @click="createAccount"
    />
  </div>
</template>
