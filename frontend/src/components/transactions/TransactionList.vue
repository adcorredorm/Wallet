<script setup lang="ts">
/**
 * Transaction List Component
 *
 * Displays list of transactions with loading and empty states
 */

import TransactionItem from './TransactionItem.vue'
import EmptyState from '@/components/shared/EmptyState.vue'
import BaseSpinner from '@/components/ui/BaseSpinner.vue'
import type { Transaction } from '@/types'

interface Props {
  transactions: Transaction[]
  loading?: boolean
  showAccount?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  showAccount: true
})

const emit = defineEmits<{
  'transaction-click': [transaction: Transaction]
  'create-click': []
}>()
</script>

<template>
  <div>
    <!-- Loading state -->
    <BaseSpinner v-if="loading" centered />

    <!-- Empty state -->
    <EmptyState
      v-else-if="transactions.length === 0"
      title="No hay transacciones"
      message="Comienza registrando tus ingresos y gastos para llevar un control de tus finanzas"
      icon="📊"
      action-text="Nueva transacción"
      @action="emit('create-click')"
    />

    <!-- Transaction list -->
    <div v-else class="space-y-2">
      <TransactionItem
        v-for="transaction in transactions"
        :key="transaction.id"
        :transaction="transaction"
        :show-account="showAccount"
        @click="emit('transaction-click', transaction)"
      />
    </div>
  </div>
</template>
