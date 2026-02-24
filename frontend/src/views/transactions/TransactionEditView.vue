<script setup lang="ts">
/**
 * Transaction Edit View
 *
 * Form to edit existing transaction
 */

import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTransactionsStore, useAccountsStore, useCategoriesStore, useUiStore } from '@/stores'
import TransactionForm from '@/components/transactions/TransactionForm.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseSpinner from '@/components/ui/BaseSpinner.vue'
import ConfirmDialog from '@/components/shared/ConfirmDialog.vue'
import type { UpdateTransactionDto } from '@/types'

const route = useRoute()
const router = useRouter()
const transactionsStore = useTransactionsStore()
const accountsStore = useAccountsStore()
const categoriesStore = useCategoriesStore()
const uiStore = useUiStore()

const transactionId = route.params.id as string
const showDeleteDialog = ref(false)
const deleting = ref(false)

const transaction = computed(() =>
  transactionsStore.transactions.find(t => t.id === transactionId)
)

const accounts = computed(() => accountsStore.activeAccounts)
const categories = computed(() => categoriesStore.categories)

onMounted(async () => {
  if (!transaction.value) {
    try {
      await transactionsStore.fetchTransactionById(transactionId)
    } catch (error: any) {
      uiStore.showError(error.message || 'Error al cargar transacción')
      router.push('/transactions')
    }
  }
})

async function handleSubmit(data: UpdateTransactionDto) {
  try {
    await transactionsStore.updateTransaction(transactionId, data)
    // Balance is updated by adjustBalance() inside updateTransaction — no API call needed.
    uiStore.showSuccess('Transacción actualizada exitosamente')
    router.push('/transactions')
  } catch (error: any) {
    uiStore.showError(error.message || 'Error al actualizar transacción')
  }
}

function handleCancel() {
  router.back()
}

async function confirmDelete() {
  deleting.value = true
  try {
    await transactionsStore.deleteTransaction(transactionId)
    // Balance is updated by adjustBalance() inside deleteTransaction — no API call needed.
    uiStore.showSuccess('Transacción eliminada exitosamente')
    router.push('/transactions')
  } catch (error: any) {
    uiStore.showError(error.message || 'Error al eliminar transacción')
  } finally {
    deleting.value = false
    showDeleteDialog.value = false
  }
}
</script>

<template>
  <div v-if="transaction" class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold">Editar Transacción</h1>
      <BaseButton variant="danger" size="sm" @click="showDeleteDialog = true">
        Eliminar
      </BaseButton>
    </div>

    <BaseCard>
      <TransactionForm
        :transaction="transaction"
        :accounts="accounts"
        :categories="categories"
        :loading="transactionsStore.loading"
        @submit="handleSubmit"
        @cancel="handleCancel"
      />
    </BaseCard>

    <!-- Delete confirmation dialog -->
    <ConfirmDialog
      :show="showDeleteDialog"
      title="Eliminar transacción"
      message="¿Estás seguro de que deseas eliminar esta transacción? Esta acción no se puede deshacer."
      confirm-text="Eliminar"
      :loading="deleting"
      @confirm="confirmDelete"
      @cancel="showDeleteDialog = false"
    />
  </div>

  <BaseSpinner v-else centered />
</template>
