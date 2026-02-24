<script setup lang="ts">
/**
 * Transfers List View
 *
 * Shows all transfers between accounts
 */

import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTransfersStore, useUiStore } from '@/stores'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseSpinner from '@/components/ui/BaseSpinner.vue'
import EmptyState from '@/components/shared/EmptyState.vue'
import SimpleFab from '@/components/ui/SimpleFab.vue'
import CurrencyDisplay from '@/components/shared/CurrencyDisplay.vue'
// Phase 5: per-item sync state badge
import SyncBadge from '@/components/sync/SyncBadge.vue'
import { formatDateRelative } from '@/utils/formatters'
import type { LocalTransfer } from '@/offline/types'

const router = useRouter()
const transfersStore = useTransfersStore()
const uiStore = useUiStore()

const transfers = computed(() => transfersStore.transfers)

onMounted(async () => {
  try {
    await transfersStore.fetchTransfers()
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Error al cargar transferencias'
    uiStore.showError(message)
  }
})

function goToTransfer(transfer: LocalTransfer) {
  router.push(`/transfers/${transfer.id}/edit`)
}

function createTransfer() {
  router.push('/transfers/new')
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div>
      <h1 class="text-2xl font-bold">Transferencias</h1>
    </div>

    <!-- Loading -->
    <BaseSpinner v-if="transfersStore.loading" centered />

    <!-- Empty state -->
    <EmptyState
      v-else-if="transfers.length === 0"
      title="No hay transferencias"
      message="Las transferencias permiten mover dinero entre tus cuentas"
      icon="💸"
      action-text="Nueva transferencia"
      @action="createTransfer"
    />

    <!-- Transfer list -->
    <div v-else class="space-y-2">
      <BaseCard
        v-for="transfer in transfers"
        :key="transfer.id"
        clickable
        @click="goToTransfer(transfer)"
      >
        <div class="flex items-center gap-3">
          <!-- Icon -->
          <div class="text-2xl flex-shrink-0">💸</div>

          <!-- Info -->
          <div class="flex-1 min-w-0">
            <!--
              Title row with SyncBadge
              Same pattern as AccountCard / TransactionItem: flex row so
              the badge sits inline with the title without breaking layout.
            -->
            <div class="flex items-center gap-2">
              <h4 class="font-medium truncate">
                {{ transfer.titulo || 'Transferencia' }}
              </h4>
              <SyncBadge
                v-if="'_sync_status' in transfer"
                :status="(transfer as LocalTransfer)._sync_status"
              />
            </div>
            <div class="text-sm text-dark-text-secondary">
              <p>{{ transfer.cuenta_origen?.nombre }} → {{ transfer.cuenta_destino?.nombre }}</p>
              <p>{{ formatDateRelative(transfer.fecha) }}</p>
            </div>
          </div>

          <!-- Amount -->
          <div class="flex-shrink-0 text-right">
            <CurrencyDisplay
              :amount="transfer.monto"
              :currency="transfer.cuenta_origen?.divisa || 'USD'"
              size="md"
            />
          </div>
        </div>
      </BaseCard>
    </div>

    <!-- Floating Action Button -->
    <SimpleFab
      aria-label="Crear nueva transferencia"
      @click="createTransfer"
    />
  </div>
</template>
