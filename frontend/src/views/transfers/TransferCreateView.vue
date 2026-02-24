<script setup lang="ts">
/**
 * Transfer Create View
 *
 * Form to create a new transfer between accounts
 */

import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useTransfersStore, useAccountsStore, useUiStore } from '@/stores'
import TransferForm from '@/components/transfers/TransferForm.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import type { CreateTransferDto } from '@/types'

const router = useRouter()
const transfersStore = useTransfersStore()
const accountsStore = useAccountsStore()
const uiStore = useUiStore()

const accounts = computed(() => accountsStore.activeAccounts)

async function handleSubmit(data: CreateTransferDto) {
  try {
    await transfersStore.createTransfer(data)
    // Balances are updated by adjustBalance() inside createTransfer — no API call needed.
    uiStore.showSuccess('Transferencia creada exitosamente')
    router.push('/transfers')
  } catch (error: any) {
    uiStore.showError(error.message || 'Error al crear transferencia')
  }
}

function handleCancel() {
  router.back()
}
</script>

<template>
  <div class="space-y-6">
    <h1 class="text-2xl font-bold">Nueva Transferencia</h1>

    <BaseCard>
      <TransferForm
        :accounts="accounts"
        :loading="transfersStore.loading"
        @submit="handleSubmit"
        @cancel="handleCancel"
      />
    </BaseCard>
  </div>
</template>
