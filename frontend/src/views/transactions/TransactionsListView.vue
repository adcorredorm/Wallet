<script setup lang="ts">
/**
 * Transactions List View
 *
 * Shows all transactions with filters
 */

import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTransactionsStore, useUiStore } from '@/stores'
import TransactionList from '@/components/transactions/TransactionList.vue'
import SimpleFab from '@/components/ui/SimpleFab.vue'

const router = useRouter()
const transactionsStore = useTransactionsStore()
const uiStore = useUiStore()

const transactions = computed(() => transactionsStore.transactions)

onMounted(async () => {
  try {
    await transactionsStore.fetchTransactions()
  } catch (error: any) {
    uiStore.showError(error.message || 'Error al cargar transacciones')
  }
})

function goToTransaction(transaction: any) {
  router.push(`/transactions/${transaction.id}/edit`)
}

function createTransaction() {
  router.push('/transactions/new')
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div>
      <h1 class="text-2xl font-bold">Transacciones</h1>
    </div>

    <!-- Transaction list -->
    <TransactionList
      :transactions="transactions"
      :loading="transactionsStore.loading"
      @transaction-click="goToTransaction"
      @create-click="createTransaction"
    />

    <!-- Floating Action Button -->
    <SimpleFab
      aria-label="Crear nueva transacción"
      @click="createTransaction"
    />
  </div>
</template>
