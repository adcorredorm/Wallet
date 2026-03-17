<script setup lang="ts">
/**
 * Transaction Create View
 *
 * Form to create a new transaction (income or expense)
 */

import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useTransactionsStore, useAccountsStore, useCategoriesStore, useUiStore } from '@/stores'
import TransactionForm from '@/components/transactions/TransactionForm.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import type { CreateTransactionDto } from '@/types'

const router = useRouter()
const route = useRoute()
const initialAccountId = route.query.account_id as string | undefined
const transactionsStore = useTransactionsStore()
const accountsStore = useAccountsStore()
const categoriesStore = useCategoriesStore()
const uiStore = useUiStore()

const accounts = computed(() => accountsStore.activeAccounts)
const categories = computed(() => categoriesStore.categories)

async function handleSubmit(data: CreateTransactionDto) {
  try {
    await transactionsStore.createTransaction(data)
    // Balance is updated by adjustBalance() inside createTransaction — no API call needed.
    uiStore.showSuccess('Transacción creada exitosamente')
    router.push('/transactions')
  } catch (error: any) {
    uiStore.showError(error.message || 'Error al crear transacción')
  }
}

function handleCancel() {
  router.back()
}
</script>

<template>
  <div class="space-y-6">
    <h1 class="text-2xl font-bold">Nueva Transacción</h1>

    <BaseCard>
      <TransactionForm
        :accounts="accounts"
        :categories="categories"
        :loading="transactionsStore.loading"
        :initial-account-id="initialAccountId"
        @submit="handleSubmit"
        @cancel="handleCancel"
      />
    </BaseCard>
  </div>
</template>
