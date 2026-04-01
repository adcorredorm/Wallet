<script setup lang="ts">
/**
 * Transfer Create View
 *
 * Form to create a new transfer between accounts
 */

import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useTransfersStore, useAccountsStore, useUiStore, useTransactionsStore } from '@/stores'
import TransferForm from '@/components/transfers/TransferForm.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import type { CreateTransferDto, UpdateTransferDto, CreateTransactionDto } from '@/types'

const router = useRouter()
const transfersStore = useTransfersStore()
const transactionsStore = useTransactionsStore()
const accountsStore = useAccountsStore()
const uiStore = useUiStore()

const accounts = computed(() => accountsStore.activeAccounts)

async function handleSubmit(data: CreateTransferDto | UpdateTransferDto, feeData?: CreateTransactionDto) {
  try {
    const transfer = await transfersStore.createTransfer(data as CreateTransferDto)

    if (feeData && transfer?.id) {
      const feePayload: CreateTransactionDto = {
        ...feeData,
        fee_for_transfer_id: transfer.id,
      }
      try {
        await transactionsStore.createTransaction(feePayload)
      } catch {
        uiStore.showError('Transferencia creada, pero hubo un error al registrar el fee.')
      }
    }

    // Balances are updated by adjustBalance() inside createTransfer — no API call needed.
    uiStore.showSuccess('Transferencia creada exitosamente')
    router.push('/')
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

    <!-- Note: no setup safety net here — transfers require 2 accounts which
         TransferForm validates inline. The FAB (the only entry point to this view)
         is already disabled when accounts are missing (DashboardView showChecklist). -->
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
