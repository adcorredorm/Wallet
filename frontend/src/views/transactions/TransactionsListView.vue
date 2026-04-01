<script setup lang="ts">
/**
 * Transactions List View
 * Data is read directly from Dexie via usePaginatedList — no backend call.
 * transactionsStore.fetchTransactions() is kept to populate shared Pinia state.
 */

import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTransactionsStore, useUiStore } from '@/stores'
import { usePaginatedList } from '@/composables/usePaginatedList'
import TransactionList from '@/components/transactions/TransactionList.vue'
import PaginationControls from '@/components/ui/PaginationControls.vue'
import SimpleFab from '@/components/ui/SimpleFab.vue'
import type { LocalTransaction } from '@/offline/types'

const router = useRouter()
const transactionsStore = useTransactionsStore()
const uiStore = useUiStore()

const PAGE_SIZE = 20

const {
  items: transactions,
  currentPage,
  totalPages,
  loading,
  goToPage,
} = usePaginatedList<LocalTransaction>('transactions', PAGE_SIZE)

onMounted(async () => {
  try {
    await transactionsStore.fetchTransactions()
  } catch (error: any) {
    uiStore.showError(error.message || 'Error al cargar transacciones')
  }
})

function goToTransaction(transaction: any) {
  router.push(`/transactions/${transaction.id}`)
}

function createTransaction() {
  router.push('/transactions/new')
}
</script>

<template>
  <div class="space-y-6 pb-24">
    <div>
      <h1 class="text-2xl font-bold">Transacciones</h1>
    </div>

    <TransactionList
      :transactions="transactions"
      :loading="loading"
      @transaction-click="goToTransaction"
      @create-click="createTransaction"
    />

    <PaginationControls
      :current-page="currentPage"
      :total-pages="totalPages"
      @page-change="goToPage"
    />

    <SimpleFab
      ariaLabel="Crear nueva transacción"
      @click="createTransaction"
    />
  </div>
</template>
