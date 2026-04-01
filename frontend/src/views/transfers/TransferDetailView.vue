<script setup lang="ts">
/**
 * Transfer Detail View
 *
 * Shows full transfer info + associated fee section.
 * Queries Dexie for fee transaction where fee_for_transfer_id === this id.
 */

import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTransfersStore, useAccountsStore, useCategoriesStore, useUiStore } from '@/stores'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseSpinner from '@/components/ui/BaseSpinner.vue'
import CurrencyDisplay from '@/components/shared/CurrencyDisplay.vue'
import { formatDateRelative } from '@/utils/formatters'
import { db } from '@/offline'
import type { LocalTransaction } from '@/offline/types'

const route = useRoute()
const router = useRouter()
const transfersStore = useTransfersStore()
const accountsStore = useAccountsStore()
const categoriesStore = useCategoriesStore()
const uiStore = useUiStore()

const transferId = route.params.id as string

const transfer = computed(() =>
  transfersStore.transfers.find(t => t.id === transferId)
)

const associatedFee = ref<LocalTransaction | null>(null)
const feeLoading = ref(true)

onMounted(async () => {
  if (!transfer.value) {
    try {
      await transfersStore.fetchTransferById(transferId)
    } catch (error: any) {
      uiStore.showError(error.message || 'Error al cargar transferencia')
      router.push('/transfers')
      return
    }
  }

  try {
    const fee = await db.transactions
      .where('fee_for_transfer_id')
      .equals(transferId)
      .first()
    associatedFee.value = fee ?? null
  } catch {
    associatedFee.value = null
  } finally {
    feeLoading.value = false
  }
})

const sourceAccount = computed(() =>
  accountsStore.accounts.find(a => a.id === transfer.value?.source_account_id)
)

const destinationAccount = computed(() =>
  accountsStore.accounts.find(a => a.id === transfer.value?.destination_account_id)
)

const feeCategory = computed(() =>
  associatedFee.value
    ? categoriesStore.categories.find(c => c.id === associatedFee.value!.category_id)
    : null
)

function goToEdit() {
  router.push(`/transfers/${transferId}/edit`)
}

function goToFee() {
  if (associatedFee.value) {
    router.push(`/transactions/${associatedFee.value.id}`)
  }
}

function addFee() {
  router.push({
    path: '/transactions/new',
    query: {
      fee_for_transfer_id: transferId,
      account_id: transfer.value?.source_account_id,
      date: transfer.value?.date,
    }
  })
}
</script>

<template>
  <div v-if="transfer" class="space-y-4 pb-24">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold truncate pr-2">
        {{ transfer.title || 'Transferencia' }}
      </h1>
      <BaseButton variant="ghost" size="sm" @click="goToEdit">
        Editar
      </BaseButton>
    </div>

    <!-- Main info card -->
    <BaseCard>
      <div class="space-y-3">
        <!-- Amount -->
        <div class="flex items-center justify-between">
          <span class="text-sm text-dark-text-secondary">Monto</span>
          <CurrencyDisplay
            :amount="transfer.amount"
            :currency="sourceAccount?.currency || 'USD'"
            size="lg"
          />
        </div>

        <!-- Date -->
        <div class="flex items-center justify-between">
          <span class="text-sm text-dark-text-secondary">Fecha</span>
          <span class="text-sm text-dark-text-primary">{{ formatDateRelative(transfer.date) }}</span>
        </div>

        <!-- Source account -->
        <div class="flex items-center justify-between">
          <span class="text-sm text-dark-text-secondary">Desde</span>
          <span class="text-sm text-dark-text-primary">{{ sourceAccount?.name || '—' }}</span>
        </div>

        <!-- Destination account -->
        <div class="flex items-center justify-between">
          <span class="text-sm text-dark-text-secondary">Hacia</span>
          <span class="text-sm text-dark-text-primary">{{ destinationAccount?.name || '—' }}</span>
        </div>

        <!-- Description -->
        <div v-if="transfer.description" class="flex items-start justify-between gap-2">
          <span class="text-sm text-dark-text-secondary shrink-0">Descripción</span>
          <span class="text-sm text-dark-text-primary text-right">{{ transfer.description }}</span>
        </div>

        <!-- Tags -->
        <div v-if="transfer.tags?.length" class="flex items-start justify-between gap-2">
          <span class="text-sm text-dark-text-secondary shrink-0">Etiquetas</span>
          <span class="text-sm text-dark-text-primary text-right">{{ transfer.tags.join(', ') }}</span>
        </div>
      </div>
    </BaseCard>

    <!-- Fee asociado section -->
    <BaseCard>
      <div class="space-y-2">
        <h2 class="text-sm font-semibold text-dark-text-secondary uppercase tracking-wide">Fee asociado</h2>

        <div v-if="feeLoading" class="text-sm text-dark-text-tertiary">Cargando...</div>

        <div v-else-if="associatedFee" class="flex items-center justify-between">
          <div>
            <CurrencyDisplay
              :amount="associatedFee.amount"
              :currency="sourceAccount?.currency || 'USD'"
              size="sm"
              class="text-error"
            />
            <p class="text-xs text-dark-text-secondary mt-0.5">
              {{ feeCategory?.icon }} {{ feeCategory?.name || '—' }}
            </p>
          </div>
          <BaseButton variant="ghost" size="sm" @click="goToFee">
            Ver fee
          </BaseButton>
        </div>

        <div v-else class="flex items-center justify-between">
          <span class="text-sm text-dark-text-secondary">Sin fee registrado</span>
          <BaseButton variant="ghost" size="sm" @click="addFee">
            Agregar fee
          </BaseButton>
        </div>
      </div>
    </BaseCard>
  </div>

  <BaseSpinner v-else centered />
</template>
