<script setup lang="ts">
/**
 * Dashboard View
 *
 * Main dashboard showing:
 * - Net worth
 * - Account balances
 * - Recent activity (paginated — transactions + transfers merged)
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
import { useMovements } from '@/composables/useMovements'
// Note: NetWorthCard is now self-contained — it reads its own stores internally.
// DashboardView only passes the `loading` flag it already controls.
import NetWorthCard from '@/components/dashboard/NetWorthCard.vue'
import NetWorthChart from '@/components/dashboard/NetWorthChart.vue'
import AccountsOverview from '@/components/dashboard/AccountsOverview.vue'
import FloatingActionButton from '@/components/ui/FloatingActionButton.vue'
import TransactionItem from '@/components/transactions/TransactionItem.vue'
import PaginationControls from '@/components/ui/PaginationControls.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseSpinner from '@/components/ui/BaseSpinner.vue'
import EmptyState from '@/components/shared/EmptyState.vue'
import SyncBadge from '@/components/sync/SyncBadge.vue'
import CurrencyDisplay from '@/components/shared/CurrencyDisplay.vue'
import { formatDateRelative } from '@/utils/formatters'
import type { Account } from '@/types'
import type { LocalTransfer } from '@/offline/types'

const router = useRouter()
const accountsStore = useAccountsStore()
const transactionsStore = useTransactionsStore()
const uiStore = useUiStore()

const loading = ref(true)

const accountsWithBalances = computed(() =>
  (accountsStore.accountsWithBalances as (Account & { balance: number })[]).filter(a => a.active !== false)
)

const PAGE_SIZE = 20
const {
  items: movements,
  currentPage,
  totalPages,
  loading: movementsLoading,
  goToPage,
} = useMovements(undefined, PAGE_SIZE)

onMounted(async () => {
  loading.value = true
  try {
    // Load from IndexedDB (Dexie-only, no network call).
    // SyncManager handles background updates via wallet:sync-complete → refreshFromDB().
    await Promise.all([
      accountsStore.fetchAccounts(),
      transactionsStore.fetchTransactions()
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

function goToTransaction(transaction: any) {
  router.push(`/transactions/${transaction.id}/edit`)
}
</script>

<template>
  <div class="space-y-6 pb-24">
    <!-- Net Worth Card -->
    <NetWorthCard :loading="loading" />

    <!-- Net Worth Evolution Chart -->
    <NetWorthChart />

    <!-- Main content grid -->
    <div class="grid gap-6 md:grid-cols-2">
      <!-- Accounts Overview -->
      <AccountsOverview
        :accounts="accountsWithBalances"
        :loading="loading"
        @account-click="goToAccount"
      />

      <!-- Actividad Reciente (transacciones + transferencias paginadas) -->
      <div>
        <h2 class="text-lg font-semibold mb-4">Actividad Reciente</h2>

        <BaseSpinner v-if="movementsLoading && movements.length === 0" centered />

        <EmptyState
          v-else-if="!movementsLoading && movements.length === 0"
          title="Sin actividad"
          message="Tus transacciones y transferencias aparecerán aquí"
          icon="📊"
        />

        <div v-else class="space-y-2">
          <template v-for="item in movements" :key="item.id">
            <TransactionItem
              v-if="item._type === 'transaction'"
              :transaction="item"
              @click="goToTransaction(item)"
            />
            <BaseCard
              v-else
              clickable
              @click="router.push(`/transfers/${item.id}/edit`)"
            >
              <div class="flex items-center gap-3">
                <div class="text-2xl flex-shrink-0">💸</div>
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2">
                    <h4 class="font-medium truncate">
                      {{ (item as LocalTransfer).title || 'Transferencia' }}
                    </h4>
                    <SyncBadge
                      v-if="'_sync_status' in item"
                      :status="(item as LocalTransfer)._sync_status"
                    />
                  </div>
                  <div class="text-sm text-dark-text-secondary">
                    <p>{{ (item as LocalTransfer).source_account?.name }} → {{ (item as LocalTransfer).destination_account?.name }}</p>
                    <p>{{ formatDateRelative((item as LocalTransfer).date) }}</p>
                  </div>
                </div>
                <div class="flex-shrink-0 text-right">
                  <CurrencyDisplay
                    :amount="(item as LocalTransfer).amount"
                    :currency="(item as LocalTransfer).source_account?.currency || 'USD'"
                    size="md"
                  />
                </div>
              </div>
            </BaseCard>
          </template>
        </div>

        <PaginationControls
          :current-page="currentPage"
          :total-pages="totalPages"
          :page-size="PAGE_SIZE"
          @page-change="goToPage"
        />
      </div>
    </div>

    <!-- Floating Action Button -->
    <FloatingActionButton />
  </div>
</template>
