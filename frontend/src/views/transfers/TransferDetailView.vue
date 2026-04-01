<script setup lang="ts">
/**
 * Transfer Detail View
 *
 * Shows full transfer info + associated fee section.
 * "Agregar fee" expands an inline mini-form directly in the Fee asociado section.
 */

import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTransfersStore, useTransactionsStore, useAccountsStore, useCategoriesStore, useUiStore } from '@/stores'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseSpinner from '@/components/ui/BaseSpinner.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import AmountInput from '@/components/shared/AmountInput.vue'
import CategorySelect from '@/components/categories/CategorySelect.vue'
import CurrencyDisplay from '@/components/shared/CurrencyDisplay.vue'
import { formatDateRelative } from '@/utils/formatters'
import { db } from '@/offline'
import type { LocalTransaction } from '@/offline/types'
import { TransactionType } from '@/types'

const route = useRoute()
const router = useRouter()
const transfersStore = useTransfersStore()
const transactionsStore = useTransactionsStore()
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

// Inline fee mini-form state
const showFeeForm = ref(false)
const feeFormType = ref<'fixed' | 'percentage'>('fixed')
const feeFormAmount = ref<number>(0)
const feeFormCategoryId = ref<string>('')
const feeFormSubmitting = ref(false)
const feeFormError = ref<string>('')

const FEE_TYPE_OPTIONS = [
  { value: 'fixed', label: 'Fijo' },
  { value: 'percentage', label: 'Porcentaje (%)' },
]

watch(showFeeForm, (active) => {
  if (active) {
    feeFormCategoryId.value = ''
    feeFormAmount.value = 0
    feeFormType.value = 'fixed'
    feeFormError.value = ''
  }
})

const computedFeeAmount = computed<number | null>(() => {
  if (feeFormType.value !== 'percentage') return null
  if (!transfer.value?.amount || feeFormAmount.value <= 0) return null
  return parseFloat(((feeFormAmount.value / 100) * Number(transfer.value.amount)).toFixed(8))
})

const resolvedFeeAmount = computed<number>(() => {
  return feeFormType.value === 'percentage' ? (computedFeeAmount.value ?? 0) : feeFormAmount.value
})

async function submitFee() {
  if (!feeFormCategoryId.value) {
    feeFormError.value = 'Selecciona una categoría'
    return
  }
  if (resolvedFeeAmount.value <= 0) {
    feeFormError.value = 'El monto debe ser mayor a 0'
    return
  }
  feeFormSubmitting.value = true
  feeFormError.value = ''
  try {
    const fee = await transactionsStore.createTransaction({
      type: TransactionType.EXPENSE,
      amount: resolvedFeeAmount.value,
      date: transfer.value!.date,
      account_id: transfer.value!.source_account_id,
      category_id: feeFormCategoryId.value,
      title: 'Fee',
      tags: [],
      fee_for_transfer_id: transferId,
    })
    associatedFee.value = fee ?? null
    showFeeForm.value = false
  } catch {
    feeFormError.value = 'Error al crear el fee'
  } finally {
    feeFormSubmitting.value = false
  }
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

        <div v-else>
          <div v-if="!showFeeForm" class="flex items-center justify-between">
            <span class="text-sm text-dark-text-secondary">Sin fee registrado</span>
            <BaseButton variant="ghost" size="sm" @click="showFeeForm = true">
              Agregar fee
            </BaseButton>
          </div>

          <!-- Inline mini fee form -->
          <div v-else class="space-y-3 pt-1">
            <BaseSelect
              v-model="feeFormType"
              label="Tipo"
              :options="FEE_TYPE_OPTIONS"
            />

            <div>
              <AmountInput
                v-model="feeFormAmount"
                label="Monto del fee"
                :currency="feeFormType === 'percentage' ? '%' : (sourceAccount?.currency || 'COP')"
                placeholder="0.00"
              />
              <p v-if="feeFormType === 'percentage' && computedFeeAmount !== null" class="mt-1 text-xs text-dark-text-tertiary">
                = {{ sourceAccount?.currency || '' }} {{ computedFeeAmount.toFixed(2) }}
              </p>
            </div>

            <CategorySelect
              v-model="feeFormCategoryId"
              label="Categoría del fee"
              :filter-type="'expense' as any"
              :error="!feeFormCategoryId ? feeFormError : ''"
            />

            <p v-if="feeFormError && feeFormCategoryId" class="text-xs text-error">{{ feeFormError }}</p>

            <div class="flex gap-2 justify-end">
              <BaseButton variant="ghost" size="sm" :disabled="feeFormSubmitting" @click="showFeeForm = false">
                Cancelar
              </BaseButton>
              <BaseButton variant="primary" size="sm" :loading="feeFormSubmitting" @click="submitFee">
                Guardar fee
              </BaseButton>
            </div>
          </div>
        </div>
      </div>
    </BaseCard>
  </div>

  <BaseSpinner v-else centered />
</template>
