<script setup lang="ts">
/**
 * Transfers List View
 * Data is read from Dexie via usePaginatedList — no backend call.
 */

import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTransfersStore, useUiStore } from '@/stores'
import { usePaginatedList } from '@/composables/usePaginatedList'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseSpinner from '@/components/ui/BaseSpinner.vue'
import EmptyState from '@/components/shared/EmptyState.vue'
import PaginationControls from '@/components/ui/PaginationControls.vue'
import SimpleFab from '@/components/ui/SimpleFab.vue'
import CurrencyDisplay from '@/components/shared/CurrencyDisplay.vue'
import SyncBadge from '@/components/sync/SyncBadge.vue'
import { formatDateRelative } from '@/utils/formatters'
import type { LocalTransfer } from '@/offline/types'

const router = useRouter()
const transfersStore = useTransfersStore()
const uiStore = useUiStore()

const PAGE_SIZE = 20

const {
  items: transfers,
  currentPage,
  totalPages,
  loading,
  goToPage,
} = usePaginatedList<LocalTransfer>('transfers', PAGE_SIZE)

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
  <div class="space-y-6 pb-24">
    <div>
      <h1 class="text-2xl font-bold">Transferencias</h1>
    </div>

    <BaseSpinner v-if="loading && transfers.length === 0" centered />

    <EmptyState
      v-else-if="!loading && transfers.length === 0"
      title="No hay transferencias"
      message="Las transferencias permiten mover dinero entre tus cuentas"
      icon="💸"
      action-text="Nueva transferencia"
      @action="createTransfer"
    />

    <div v-else class="space-y-2">
      <BaseCard
        v-for="transfer in transfers"
        :key="transfer.id"
        clickable
        @click="goToTransfer(transfer)"
      >
        <div class="flex items-center gap-3">
          <div class="text-2xl flex-shrink-0">💸</div>
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2">
              <h4 class="font-medium truncate">
                {{ transfer.title || 'Transferencia' }}
              </h4>
              <SyncBadge
                v-if="'_sync_status' in transfer"
                :status="transfer._sync_status"
              />
            </div>
            <div class="text-sm text-dark-text-secondary">
              <p>{{ transfer.source_account?.name }} → {{ transfer.destination_account?.name }}</p>
              <p>{{ formatDateRelative(transfer.date) }}</p>
            </div>
          </div>
          <div class="flex-shrink-0 text-right">
            <CurrencyDisplay
              :amount="transfer.amount"
              :currency="transfer.source_account?.currency || 'USD'"
              size="md"
            />
          </div>
        </div>
      </BaseCard>
    </div>

    <PaginationControls
      :current-page="currentPage"
      :total-pages="totalPages"
      :page-size="PAGE_SIZE"
      @page-change="goToPage"
    />

    <SimpleFab
      ariaLabel="Crear nueva transferencia"
      @click="createTransfer"
    />
  </div>
</template>
