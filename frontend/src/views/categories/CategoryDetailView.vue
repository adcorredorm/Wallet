<script setup lang="ts">
/**
 * Category Detail View
 *
 * Shows category header, income/expense/count stats panel, and a paginated
 * list of transactions for the category. Mirrors AccountDetailView patterns.
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCategoriesStore, useAccountsStore, useUiStore } from '@/stores'
import { useExchangeRatesStore } from '@/stores/exchangeRates'
import { useSettingsStore } from '@/stores/settings'
import { useTransactionsByCategory } from '@/composables/useTransactionsByCategory'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseSpinner from '@/components/ui/BaseSpinner.vue'
import TransactionItem from '@/components/transactions/TransactionItem.vue'
import EmptyState from '@/components/shared/EmptyState.vue'
import SyncBadge from '@/components/sync/SyncBadge.vue'
import ConfirmDialog from '@/components/shared/ConfirmDialog.vue'
import PaginationControls from '@/components/ui/PaginationControls.vue'
import CurrencyDisplay from '@/components/shared/CurrencyDisplay.vue'
import { formatCategoryType } from '@/utils/formatters'
import { db } from '@/offline'

const route = useRoute()
const router = useRouter()
const categoriesStore = useCategoriesStore()
const accountsStore = useAccountsStore()
const uiStore = useUiStore()
const exchangeRatesStore = useExchangeRatesStore()
const settingsStore = useSettingsStore()

const categoryId = route.params.id as string

// Dialog visibility refs — one per action type
const showArchiveDialog = ref(false)
const showDeleteDialog = ref(false)

// Loading refs — tracked independently per action
const archiving = ref(false)
const deleting = ref(false)

// Guard: hard-delete is disabled when there are transactions.
// Default true keeps button disabled until resolved (safe default).
const hasMovements = ref(true)

// Stats panel — full aggregate over ALL transactions for this category
// Converted to primary currency (transactions may span multiple account currencies)
const statsIncome = ref(0)
const statsExpense = ref(0)
const statsTxCount = ref(0)

const category = computed(() =>
  categoriesStore.categories.find(c => c.id === categoryId)
)

const isArchived = computed(() => category.value?.active === false)

const parentCategoryName = computed(() => {
  const parentId = category.value?.parent_category_id
  if (!parentId) return null
  return categoriesStore.categories.find(c => c.id === parentId)?.name ?? null
})

const PAGE_SIZE = 20
const {
  items: transactions,
  currentPage,
  totalPages,
  loading: transactionsLoading,
  goToPage,
} = useTransactionsByCategory(categoryId, PAGE_SIZE)

async function fetchStats() {
  try {
    const txs = await db.transactions.where('category_id').equals(categoryId).toArray()
    let income = 0
    let expense = 0
    for (const tx of txs) {
      const acct = accountsStore.accounts.find(a => a.id === tx.account_id)
      const currency = acct?.currency ?? settingsStore.primaryCurrency
      const inPrimary = exchangeRatesStore.convert(Number(tx.amount), currency, settingsStore.primaryCurrency)
      if (tx.type === 'income') income += inPrimary
      else expense += inPrimary
    }
    statsIncome.value = income
    statsExpense.value = expense
    statsTxCount.value = txs.length
  } catch {
    // Non-critical — stats panel shows 0 on error
  }
}

onMounted(async () => {
  try {
    await categoriesStore.fetchCategoryById(categoryId)
  } catch (error: any) {
    uiStore.showError(error.message || 'Error al cargar categoría')
    router.push('/categories')
    return
  }

  try {
    const txCount = await db.transactions.where('category_id').equals(categoryId).count()
    hasMovements.value = txCount > 0
  } catch {
    // On error leave hasMovements = true (safe default — keeps hard-delete disabled)
  }

  void fetchStats()
})

const onStatsSync = () => void fetchStats()
onMounted(() => window.addEventListener('wallet:sync-complete', onStatsSync))
onUnmounted(() => window.removeEventListener('wallet:sync-complete', onStatsSync))

function editCategory() {
  router.push(`/categories/${categoryId}/edit`)
}

async function confirmArchive() {
  archiving.value = true
  try {
    await categoriesStore.archiveCategory(categoryId)
    uiStore.showSuccess('Categoría archivada exitosamente')
    router.push('/categories')
  } catch (error: any) {
    uiStore.showError(error.message || 'Error al archivar categoría')
  } finally {
    archiving.value = false
    showArchiveDialog.value = false
  }
}

async function confirmHardDelete() {
  deleting.value = true
  try {
    await categoriesStore.hardDeleteCategory(categoryId)
    uiStore.showSuccess('Categoría eliminada permanentemente')
    router.push('/categories')
  } catch (error: any) {
    uiStore.showError(error.message || 'Error al eliminar categoría')
  } finally {
    deleting.value = false
    showDeleteDialog.value = false
  }
}

async function restoreCategory() {
  try {
    await categoriesStore.restoreCategory(categoryId)
    uiStore.showSuccess('Categoría activada exitosamente')
  } catch (error: any) {
    uiStore.showError(error.message || 'Error al activar categoría')
  }
}

function goToTransaction(transaction: any) {
  router.push(`/transactions/${transaction.id}/edit`)
}
</script>

<template>
  <div v-if="category" class="space-y-6 pb-24">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3 min-w-0">
        <span class="text-3xl flex-shrink-0">{{ category.icon || '📁' }}</span>
        <div class="min-w-0">
          <div class="flex items-center gap-2">
            <h1 class="text-2xl font-bold truncate">{{ category.name }}</h1>
            <span
              v-if="isArchived"
              class="text-xs text-gray-400 dark:text-gray-500 shrink-0"
            >
              Archivada
            </span>
            <SyncBadge v-if="category._sync_status" :status="category._sync_status" />
          </div>
          <p class="text-sm text-dark-text-secondary">
            {{ formatCategoryType(category.type) }}
            <template v-if="parentCategoryName">
              · {{ parentCategoryName }}
            </template>
          </p>
        </div>
      </div>

      <div class="flex gap-2 shrink-0">
        <!-- Edit button — always visible -->
        <BaseButton variant="secondary" size="sm" @click="editCategory">
          Editar
        </BaseButton>

        <!-- Active category: show Archive + Hard Delete -->
        <template v-if="!isArchived">
          <BaseButton
            variant="secondary"
            size="sm"
            :loading="archiving"
            @click="showArchiveDialog = true"
          >
            Archivar
          </BaseButton>

          <span v-if="hasMovements" class="relative inline-flex group">
            <BaseButton
              variant="danger"
              size="sm"
              :disabled="true"
              class="opacity-50 cursor-not-allowed pointer-events-none"
            >
              Borrar permanentemente
            </BaseButton>
            <span class="pointer-events-none absolute top-full left-1/2 -translate-x-1/2 mt-2 w-56 rounded-md bg-yellow-900/90 border border-yellow-600/50 px-3 py-2 text-xs text-yellow-200 shadow-lg opacity-0 group-hover:opacity-100 transition-opacity duration-150 text-center z-10">
              ⚠ No se puede borrar una categoría con transacciones. Usa Archivar.
            </span>
          </span>
          <BaseButton
            v-else
            variant="danger"
            size="sm"
            :loading="deleting"
            @click="showDeleteDialog = true"
          >
            Borrar permanentemente
          </BaseButton>
        </template>

        <!-- Archived category: show Activar -->
        <BaseButton
          v-else
          variant="primary"
          size="sm"
          :loading="categoriesStore.loading"
          @click="restoreCategory"
        >
          Activar
        </BaseButton>
      </div>
    </div>

    <!-- Stats panel -->
    <div class="grid grid-cols-3 gap-3">
      <BaseCard padding="sm">
        <div class="text-center">
          <p class="text-xs text-dark-text-secondary mb-1">Ingresos</p>
          <CurrencyDisplay
            :amount="statsIncome"
            :currency="settingsStore.primaryCurrency"
            size="sm"
            class="text-green-400 font-semibold"
          />
        </div>
      </BaseCard>
      <BaseCard padding="sm">
        <div class="text-center">
          <p class="text-xs text-dark-text-secondary mb-1">Gastos</p>
          <CurrencyDisplay
            :amount="statsExpense"
            :currency="settingsStore.primaryCurrency"
            size="sm"
            class="text-red-400 font-semibold"
          />
        </div>
      </BaseCard>
      <BaseCard padding="sm">
        <div class="text-center">
          <p class="text-xs text-dark-text-secondary mb-1">Transacciones</p>
          <p class="text-base font-semibold">{{ statsTxCount }}</p>
        </div>
      </BaseCard>
    </div>

    <!-- Transaction list -->
    <div>
      <h2 class="text-lg font-semibold mb-4">Transacciones</h2>

      <BaseSpinner v-if="transactionsLoading && transactions.length === 0" centered />

      <EmptyState
        v-else-if="!transactionsLoading && transactions.length === 0"
        title="Sin transacciones"
        message="No hay transacciones en esta categoría"
        icon="🏷️"
        action-text="Nueva transacción"
        @action="router.push({ path: '/transactions/new', query: { category_id: categoryId } })"
      />

      <div v-else class="space-y-2">
        <TransactionItem
          v-for="tx in transactions"
          :key="tx.id"
          :transaction="tx"
          :show-account="true"
          @click="goToTransaction(tx)"
        />
      </div>

      <PaginationControls
        :current-page="currentPage"
        :total-pages="totalPages"
        @page-change="goToPage"
      />
    </div>

    <!-- Archive confirmation dialog -->
    <ConfirmDialog
      :show="showArchiveDialog"
      variant="warning"
      title="Archivar categoría"
      message="¿Archivar esta categoría? Dejará de aparecer en los formularios, pero todas las transacciones asociadas se conservarán intactas en el historial."
      confirm-text="Archivar"
      :loading="archiving"
      @confirm="confirmArchive"
      @cancel="showArchiveDialog = false"
    />

    <!-- Hard delete confirmation dialog -->
    <ConfirmDialog
      :show="showDeleteDialog"
      variant="danger"
      title="Borrar permanentemente"
      message="¿Borrar esta categoría permanentemente? Esta acción no se puede deshacer."
      confirm-text="Borrar"
      :loading="deleting"
      @confirm="confirmHardDelete"
      @cancel="showDeleteDialog = false"
    />
  </div>

  <!-- Loading state -->
  <BaseSpinner v-else centered />
</template>
