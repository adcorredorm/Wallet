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
import { dashboardApi } from '@/api/dashboard'
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
const netWorth = ref(0)

const accountsWithBalances = computed(() =>
  accountsStore.accountsWithBalances as (Account & { balance: number })[]
)

const recentTransactions = computed(() =>
  transactionsStore.transactions.slice(0, 5)
)

onMounted(async () => {
  try {
    loading.value = true

    // Fetch accounts with balances
    await accountsStore.fetchAccounts(true) // true = active only

    // Fetch dashboard summary data
    const summary = await dashboardApi.getSummary()

    // Calculate net worth from patrimonio_neto.balances
    if (summary.patrimonio_neto && summary.patrimonio_neto.balances) {
      netWorth.value = summary.patrimonio_neto.balances.reduce(
        (sum: number, balance: any) => sum + balance.total,
        0
      )
    } else {
      netWorth.value = 0
    }

    // Fetch recent transactions
    await transactionsStore.fetchTransactions({ limit: 5 })
  } catch (error: any) {
    uiStore.showError(error.message || 'Error al cargar el dashboard')
  } finally {
    loading.value = false
  }
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
