<script setup lang="ts">
/**
 * Dashboard View
 *
 * Main dashboard showing:
 * - Net worth
 * - Account balances
 * - Recent transactions
 * - FAB for quick actions (transaction/transfer creation)
 *
 * Why this layout?
 * - Mobile-first: Cards stack vertically
 * - Desktop: Grid layout for better use of space
 * - Most important info (net worth) at top
 * - FAB provides quick access to primary actions without cluttering the layout
 *
 * Quick actions removed:
 * - Old button grid (4 buttons) replaced with FAB
 * - Account creation moved to accounts list view
 * - Category management accessed via drawer navigation
 */

import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAccountsStore, useTransactionsStore, useUiStore } from '@/stores'
import NetWorthCard from '@/components/dashboard/NetWorthCard.vue'
import AccountsOverview from '@/components/dashboard/AccountsOverview.vue'
import RecentActivity from '@/components/dashboard/RecentActivity.vue'
import FloatingActionButton from '@/components/ui/FloatingActionButton.vue'
import type { Account, Transaction } from '@/types'

const router = useRouter()
const accountsStore = useAccountsStore()
const transactionsStore = useTransactionsStore()
const uiStore = useUiStore()

const loading = ref(true)

const accountsWithBalances = computed(() =>
  accountsStore.accountsWithBalances as (Account & { balance: number })[]
)

const recentTransactions = computed(() =>
  transactionsStore.transactions.slice(0, 5)
)

// netWorth is always derived locally from accountsWithBalances.
// Using a server override (dashboardApi.getSummary) would cause the net worth
// to show a stale value whenever there are unsynced offline transactions.
// The local sum is always correct because adjustBalance() keeps IndexedDB
// and balances.value in sync with every write.
const netWorth = computed(() =>
  accountsStore.accountsWithBalances.reduce((sum, a) => sum + (a.balance ?? 0), 0)
)

onMounted(async () => {
  loading.value = true
  try {
    // Step 1 — Load from IndexedDB immediately (non-blocking, returns fast).
    // Both calls return cached data right away; background revalidation will
    // update the reactive refs when the network responds.
    await Promise.all([
      accountsStore.fetchAccounts(true),
      transactionsStore.fetchTransactions({ limit: 5 })
    ])
  } catch (error: any) {
    uiStore.showError(error.message || 'Error al cargar el dashboard')
  } finally {
    // Unblock the UI as soon as IndexedDB has been read.
    loading.value = false
  }

  // Balance is kept accurate by adjustBalance() on every write (persisted to
  // IndexedDB). After sync, recomputeBalancesFromTransactions() recomputes
  // from the full local history. No backend balance endpoint is ever called.
})

function goToAccount(account: Account) {
  router.push(`/accounts/${account.id}`)
}

function goToTransaction(transaction: Transaction) {
  router.push(`/transactions/${transaction.id}/edit`)
}
</script>

<template>
  <div class="space-y-6">
    <!-- Net Worth Card -->
    <NetWorthCard :net-worth="netWorth" :loading="loading" />

    <!-- Main content grid -->
    <div class="grid gap-6 md:grid-cols-2">
      <!-- Accounts Overview -->
      <AccountsOverview
        :accounts="accountsWithBalances"
        :loading="loading"
        @account-click="goToAccount"
      />

      <!-- Recent Activity -->
      <RecentActivity
        :transactions="recentTransactions"
        :loading="transactionsStore.loading"
        @transaction-click="goToTransaction"
      />
    </div>

    <!-- Floating Action Button -->
    <FloatingActionButton />
  </div>
</template>
