<script setup lang="ts">
/**
 * Transaction Detail View
 *
 * Shows full transaction info + associated fee section.
 * Queries Dexie directly for a fee transaction (fee_for_transaction_id === this id).
 * "Agregar fee" button opens TransactionCreateView pre-filled with fee_for_transaction_id.
 */

import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTransactionsStore, useAccountsStore, useCategoriesStore, useUiStore } from '@/stores'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseSpinner from '@/components/ui/BaseSpinner.vue'
import CurrencyDisplay from '@/components/shared/CurrencyDisplay.vue'
import { formatDateRelative } from '@/utils/formatters'
import { db } from '@/offline'
import type { LocalTransaction } from '@/offline/types'

const route = useRoute()
const router = useRouter()
const transactionsStore = useTransactionsStore()
const accountsStore = useAccountsStore()
const categoriesStore = useCategoriesStore()
const uiStore = useUiStore()

const transactionId = route.params.id as string

const transaction = computed(() =>
  transactionsStore.transactions.find(t => t.id === transactionId)
)

// Fee associated with this transaction (queried from Dexie)
const associatedFee = ref<LocalTransaction | null>(null)
const feeLoading = ref(true)

onMounted(async () => {
  if (!transaction.value) {
    try {
      await transactionsStore.fetchTransactionById(transactionId)
    } catch (error: any) {
      uiStore.showError(error.message || 'Error al cargar transacción')
      router.push('/transactions')
      return
    }
  }

  // Query Dexie for fee linked to this transaction
  try {
    const fee = await db.transactions
      .where('fee_for_transaction_id')
      .equals(transactionId)
      .first()
    associatedFee.value = fee ?? null
  } catch {
    associatedFee.value = null
  } finally {
    feeLoading.value = false
  }
})

const account = computed(() =>
  accountsStore.accounts.find(a => a.id === transaction.value?.account_id)
)

const category = computed(() =>
  categoriesStore.categories.find(c => c.id === transaction.value?.category_id)
)

const feeCategory = computed(() =>
  associatedFee.value
    ? categoriesStore.categories.find(c => c.id === associatedFee.value!.category_id)
    : null
)

// Is this transaction itself a fee for something else?
const isFeeTransaction = computed(() =>
  !!(transaction.value as any)?.fee_for_transaction_id ||
  !!(transaction.value as any)?.fee_for_transfer_id
)

const parentTransactionId = computed<string | null>(() =>
  (transaction.value as any)?.fee_for_transaction_id ?? null
)

const parentTransferId = computed<string | null>(() =>
  (transaction.value as any)?.fee_for_transfer_id ?? null
)

const parentTransaction = computed(() =>
  parentTransactionId.value
    ? transactionsStore.transactions.find(t => t.id === parentTransactionId.value)
    : null
)

function goToEdit() {
  router.push(`/transactions/${transactionId}/edit`)
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
      fee_for_transaction_id: transactionId,
      account_id: transaction.value?.account_id,
      date: transaction.value?.date,
    }
  })
}

function goToParentTransaction() {
  if (parentTransactionId.value) {
    router.push(`/transactions/${parentTransactionId.value}`)
  }
}

function goToParentTransfer() {
  if (parentTransferId.value) {
    router.push(`/transfers/${parentTransferId.value}`)
  }
}
</script>

<template>
  <div v-if="transaction" class="space-y-4 pb-24">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold truncate pr-2">
        {{ transaction.title || category?.name || 'Transacción' }}
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
            :amount="transaction.type === 'income' ? transaction.amount : -transaction.amount"
            :currency="account?.currency || 'USD'"
            size="lg"
            show-sign
            :class="transaction.type === 'income' ? 'text-success' : 'text-error'"
          />
        </div>

        <!-- Type -->
        <div class="flex items-center justify-between">
          <span class="text-sm text-dark-text-secondary">Tipo</span>
          <span class="text-sm text-dark-text-primary capitalize">
            {{ transaction.type === 'income' ? 'Ingreso' : 'Gasto' }}
          </span>
        </div>

        <!-- Date -->
        <div class="flex items-center justify-between">
          <span class="text-sm text-dark-text-secondary">Fecha</span>
          <span class="text-sm text-dark-text-primary">{{ formatDateRelative(transaction.date) }}</span>
        </div>

        <!-- Account -->
        <div class="flex items-center justify-between">
          <span class="text-sm text-dark-text-secondary">Cuenta</span>
          <span class="text-sm text-dark-text-primary">{{ account?.name || '—' }}</span>
        </div>

        <!-- Category -->
        <div class="flex items-center justify-between">
          <span class="text-sm text-dark-text-secondary">Categoría</span>
          <span class="text-sm text-dark-text-primary">
            {{ category?.icon }} {{ category?.name || '—' }}
          </span>
        </div>

        <!-- Description -->
        <div v-if="transaction.description" class="flex items-start justify-between gap-2">
          <span class="text-sm text-dark-text-secondary shrink-0">Descripción</span>
          <span class="text-sm text-dark-text-primary text-right">{{ transaction.description }}</span>
        </div>

        <!-- Tags -->
        <div v-if="transaction.tags?.length" class="flex items-start justify-between gap-2">
          <span class="text-sm text-dark-text-secondary shrink-0">Etiquetas</span>
          <span class="text-sm text-dark-text-primary text-right">{{ transaction.tags.join(', ') }}</span>
        </div>
      </div>
    </BaseCard>

    <!-- "Fee de:" section — shown when this transaction IS a fee for another -->
    <BaseCard v-if="isFeeTransaction">
      <div class="space-y-2">
        <h2 class="text-sm font-semibold text-dark-text-secondary uppercase tracking-wide">Fee de</h2>
        <div v-if="parentTransaction" class="flex items-center justify-between">
          <div>
            <p class="text-sm text-dark-text-primary font-medium">
              {{ parentTransaction.title || category?.name || 'Transacción' }}
            </p>
            <CurrencyDisplay
              :amount="parentTransaction.amount"
              :currency="account?.currency || 'USD'"
              size="sm"
              class="text-dark-text-secondary"
            />
          </div>
          <BaseButton variant="ghost" size="sm" @click="goToParentTransaction">
            Ver
          </BaseButton>
        </div>
        <div v-else-if="parentTransferId" class="flex items-center justify-between">
          <span class="text-sm text-dark-text-secondary">Transferencia</span>
          <BaseButton variant="ghost" size="sm" @click="goToParentTransfer">
            Ver transferencia
          </BaseButton>
        </div>
        <p v-else class="text-sm text-dark-text-tertiary">Transacción original no encontrada</p>
      </div>
    </BaseCard>

    <!-- "Fee asociado" section — shown when this is a normal transaction (not a fee itself) -->
    <BaseCard v-if="!isFeeTransaction">
      <div class="space-y-2">
        <h2 class="text-sm font-semibold text-dark-text-secondary uppercase tracking-wide">Fee asociado</h2>

        <div v-if="feeLoading" class="text-sm text-dark-text-tertiary">Cargando...</div>

        <div v-else-if="associatedFee" class="flex items-center justify-between">
          <div>
            <CurrencyDisplay
              :amount="associatedFee.amount"
              :currency="account?.currency || 'USD'"
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
