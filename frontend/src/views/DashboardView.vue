<script setup lang="ts">
/**
 * Dashboard View
 *
 * Main dashboard showing:
 * - Net worth (always visible, shows 0 when no transactions)
 * - Setup checklist (replaces chart when user has no accounts OR no categories)
 * - Net worth evolution chart (shown once both prerequisites are met)
 * - Recent activity (transactions + transfers merged, paginated)
 * - FAB for quick actions (disabled until setup is complete)
 *
 * Why this layout?
 * - Mobile-first: Cards stack vertically
 * - Most important info (net worth) always at top
 * - Setup checklist guides first-time users before they can create transactions
 * - Accounts list removed: accessible via dedicated /accounts tab
 * - FAB disabled state prevents navigation to transaction form with no accounts/categories
 */

import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAccountsStore, useTransactionsStore, useCategoriesStore, useUiStore } from '@/stores'
import { useMovements } from '@/composables/useMovements'
import NetWorthCard from '@/components/dashboard/NetWorthCard.vue'
import NetWorthChart from '@/components/dashboard/NetWorthChart.vue'
import SetupChecklist from '@/components/dashboard/SetupChecklist.vue'
import FloatingActionButton from '@/components/ui/FloatingActionButton.vue'
import TransactionItem from '@/components/transactions/TransactionItem.vue'
import PaginationControls from '@/components/ui/PaginationControls.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseSpinner from '@/components/ui/BaseSpinner.vue'
import EmptyState from '@/components/shared/EmptyState.vue'
import SyncBadge from '@/components/sync/SyncBadge.vue'
import CurrencyDisplay from '@/components/shared/CurrencyDisplay.vue'
import { formatDateRelative } from '@/utils/formatters'
import type { LocalTransfer } from '@/offline/types'

const router = useRouter()
const accountsStore = useAccountsStore()
const transactionsStore = useTransactionsStore()
const categoriesStore = useCategoriesStore()
const uiStore = useUiStore()

const loading = ref(true)

/**
 * True when the user is missing at least one account OR one category.
 * Triggers the setup checklist and disables the FAB.
 */
const showChecklist = computed(
  () => accountsStore.activeAccounts.length === 0 || categoriesStore.activeCategories.length === 0
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
      transactionsStore.fetchTransactions(),
      categoriesStore.fetchCategories(),
    ])
  } catch (error: any) {
    uiStore.showError(error.message || 'Error al cargar el dashboard')
  } finally {
    // Unblock the UI as soon as IndexedDB has been read.
    loading.value = false
  }
})

function goToTransaction(transaction: any) {
  router.push(`/transactions/${transaction.id}/edit`)
}
</script>

<template>
  <div class="space-y-6 pb-24">
    <!-- Net Worth Card — always visible (shows 0 when no transactions) -->
    <NetWorthCard :loading="loading" />

    <!-- Chart area: setup checklist OR patrimony chart -->
    <Transition name="fade" mode="out-in">
      <SetupChecklist v-if="showChecklist" key="checklist" />
      <NetWorthChart v-else key="chart" />
    </Transition>

    <!-- Recent activity (transactions + transfers merged) -->
    <div>
      <h2 class="text-lg font-semibold mb-4">Actividad Reciente</h2>

      <BaseSpinner v-if="movementsLoading && movements.length === 0" centered />

      <EmptyState
        v-else-if="!movementsLoading && movements.length === 0"
        title="Sin actividad"
        message="Tus transacciones y transferencias aparecerán aquí"
        icon="📊"
        :action-text="showChecklist ? '' : 'Nueva transacción'"
        @action="router.push('/transactions/new')"
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
        @page-change="goToPage"
      />
    </div>

    <!-- FAB: disabled when setup prerequisites are missing -->
    <FloatingActionButton :disabled="showChecklist" />
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 200ms ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
