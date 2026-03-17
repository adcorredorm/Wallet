<script setup lang="ts">
/**
 * Transaction Create View
 *
 * Form to create a new transaction (income or expense).
 *
 * Safety net: if the user has no accounts OR no categories, the form is
 * replaced with an EmptyState that guides them back to the dashboard to
 * complete setup. This handles direct URL navigation to /transactions/new
 * before prerequisites are met (e.g., deep link, back-button quirk).
 *
 * On success: redirects to / (home) so the user lands on the dashboard
 * where they can see their updated activity.
 */

import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useTransactionsStore, useAccountsStore, useCategoriesStore, useUiStore } from '@/stores'
import TransactionForm from '@/components/transactions/TransactionForm.vue'
import EmptyState from '@/components/shared/EmptyState.vue'
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

/** True when prerequisites for transaction creation are missing */
const needsSetup = computed(
  () => accountsStore.activeAccounts.length === 0 || categoriesStore.activeCategories.length === 0
)

async function handleSubmit(data: CreateTransactionDto) {
  try {
    await transactionsStore.createTransaction(data)
    uiStore.showSuccess('Transacción creada exitosamente')
    router.push('/')
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

    <!-- Safety net: shown when account or category prerequisites are missing -->
    <EmptyState
      v-if="needsSetup"
      icon="🔒"
      title="Configura tu wallet primero"
      message="Necesitas al menos una cuenta y una categoría para crear transacciones"
      action-text="Ir al inicio"
      @action="router.push('/')"
    />

    <BaseCard v-else>
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
