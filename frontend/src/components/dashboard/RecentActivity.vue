<script setup lang="ts">
/**
 * Recent Activity Component
 *
 * Shows recent transactions in dashboard
 */

import TransactionItem from '@/components/transactions/TransactionItem.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import type { Transaction } from '@/types'

interface Props {
  transactions: Transaction[]
  loading?: boolean
}

withDefaults(defineProps<Props>(), {
  loading: false
})

const emit = defineEmits<{
  'transaction-click': [transaction: Transaction]
}>()
</script>

<template>
  <div>
    <!-- Header -->
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-lg font-semibold">Actividad Reciente</h2>
      <router-link
        to="/transactions"
        class="text-sm text-accent-blue hover:underline"
      >
        Ver todas
      </router-link>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex justify-center py-8">
      <div class="spinner w-8 h-8"></div>
    </div>

    <!-- Recent transactions -->
    <div v-else-if="transactions.length > 0" class="space-y-2">
      <TransactionItem
        v-for="transaction in transactions.slice(0, 5)"
        :key="transaction.id"
        :transaction="transaction"
        @click="emit('transaction-click', transaction)"
      />
    </div>

    <!-- Empty state -->
    <BaseCard v-else>
      <div class="text-center py-6">
        <p class="text-4xl mb-2">📊</p>
        <p class="text-dark-text-secondary">No hay transacciones recientes</p>
        <router-link
          to="/transactions/new"
          class="inline-block mt-4 btn-primary"
        >
          Crear transacción
        </router-link>
      </div>
    </BaseCard>
  </div>
</template>
