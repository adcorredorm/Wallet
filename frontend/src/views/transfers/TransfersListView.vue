<script setup lang="ts">
/**
 * Transfers List View
 * Data is read from Dexie via usePaginatedList — no backend call.
 */

import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTransfersStore, useUiStore, useAccountsStore } from '@/stores'
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
const accountsStore = useAccountsStore()
const uiStore = useUiStore()

/**
 * Resolves an account name from its ID using the in-memory accounts store.
 * Returns a fallback string so the UI never shows undefined.
 */
function getAccountName(id: string): string {
  return accountsStore.accounts.find(a => a.id === id)?.name ?? 'Cuenta desconocida'
}

/**
 * Resolves an account currency from its ID using the in-memory accounts store.
 * Falls back to 'USD' to avoid breaking CurrencyDisplay.
 */
function getAccountCurrency(id: string): string {
  return accountsStore.accounts.find(a => a.id === id)?.currency ?? 'USD'
}

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
  router.push(`/transfers/${transfer.id}`)
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
              <p>{{ getAccountName(transfer.source_account_id) }} → {{ getAccountName(transfer.destination_account_id) }}</p>
              <p>{{ formatDateRelative(transfer.date) }}</p>
            </div>
          </div>
          <div class="flex-shrink-0 text-right">
            <CurrencyDisplay
              :amount="transfer.amount"
              :currency="getAccountCurrency(transfer.source_account_id)"
              size="md"
            />
          </div>
        </div>
      </BaseCard>
    </div>

    <PaginationControls
      :current-page="currentPage"
      :total-pages="totalPages"
      @page-change="goToPage"
    />

    <SimpleFab
      ariaLabel="Crear nueva transferencia"
      @click="createTransfer"
    />
  </div>
</template>
