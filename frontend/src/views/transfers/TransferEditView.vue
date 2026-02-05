<script setup lang="ts">
/**
 * Transfer Edit View
 *
 * Form to edit existing transfer
 */

import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTransfersStore, useAccountsStore, useUiStore } from '@/stores'
import TransferForm from '@/components/transfers/TransferForm.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseSpinner from '@/components/ui/BaseSpinner.vue'
import ConfirmDialog from '@/components/shared/ConfirmDialog.vue'
import type { UpdateTransferDto } from '@/types'

const route = useRoute()
const router = useRouter()
const transfersStore = useTransfersStore()
const accountsStore = useAccountsStore()
const uiStore = useUiStore()

const transferId = route.params.id as string
const showDeleteDialog = ref(false)
const deleting = ref(false)

const transfer = computed(() =>
  transfersStore.transfers.find(t => t.id === transferId)
)

const accounts = computed(() => accountsStore.activeAccounts)

onMounted(async () => {
  if (!transfer.value) {
    try {
      await transfersStore.fetchTransferById(transferId)
    } catch (error: any) {
      uiStore.showError(error.message || 'Error al cargar transferencia')
      router.push('/transfers')
    }
  }
})

async function handleSubmit(data: UpdateTransferDto) {
  try {
    await transfersStore.updateTransfer(transferId, data)
    // Refresh balances
    const origenId = data.cuenta_origen_id || transfer.value?.cuenta_origen_id
    const destinoId = data.cuenta_destino_id || transfer.value?.cuenta_destino_id
    if (origenId && destinoId) {
      await Promise.all([
        accountsStore.fetchBalance(origenId),
        accountsStore.fetchBalance(destinoId)
      ])
    }
    uiStore.showSuccess('Transferencia actualizada exitosamente')
    router.push('/transfers')
  } catch (error: any) {
    uiStore.showError(error.message || 'Error al actualizar transferencia')
  }
}

function handleCancel() {
  router.back()
}

async function confirmDelete() {
  deleting.value = true
  try {
    const origenId = transfer.value?.cuenta_origen_id
    const destinoId = transfer.value?.cuenta_destino_id
    await transfersStore.deleteTransfer(transferId)
    if (origenId && destinoId) {
      await Promise.all([
        accountsStore.fetchBalance(origenId),
        accountsStore.fetchBalance(destinoId)
      ])
    }
    uiStore.showSuccess('Transferencia eliminada exitosamente')
    router.push('/transfers')
  } catch (error: any) {
    uiStore.showError(error.message || 'Error al eliminar transferencia')
  } finally {
    deleting.value = false
    showDeleteDialog.value = false
  }
}
</script>

<template>
  <div v-if="transfer" class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold">Editar Transferencia</h1>
      <BaseButton variant="danger" size="sm" @click="showDeleteDialog = true">
        Eliminar
      </BaseButton>
    </div>

    <BaseCard>
      <TransferForm
        :transfer="transfer"
        :accounts="accounts"
        :loading="transfersStore.loading"
        @submit="handleSubmit"
        @cancel="handleCancel"
      />
    </BaseCard>

    <!-- Delete confirmation dialog -->
    <ConfirmDialog
      :show="showDeleteDialog"
      title="Eliminar transferencia"
      message="¿Estás seguro de que deseas eliminar esta transferencia? Esta acción no se puede deshacer."
      confirm-text="Eliminar"
      :loading="deleting"
      @confirm="confirmDelete"
      @cancel="showDeleteDialog = false"
    />
  </div>

  <BaseSpinner v-else centered />
</template>
