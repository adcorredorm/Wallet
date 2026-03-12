<script setup lang="ts">
/**
 * Transaction Form Component
 *
 * Form for creating/editing income/expense transactions
 * Mobile-optimized with validation
 */

import { ref, reactive, computed, watch } from 'vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import AmountInput from '@/components/shared/AmountInput.vue'
import DatePicker from '@/components/shared/DatePicker.vue'
import AccountSelect from '@/components/accounts/AccountSelect.vue'
import CategorySelect from '@/components/categories/CategorySelect.vue'
import { TRANSACTION_TYPES } from '@/utils/constants'
import { required, positiveNumber } from '@/utils/validators'
import { formatDateForInput } from '@/utils/formatters'
import type { Transaction, CreateTransactionDto, UpdateTransactionDto, TransactionType, Account, Category } from '@/types'

interface Props {
  transaction?: Transaction
  accounts: Account[]
  categories: Category[]
  loading?: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  submit: [data: CreateTransactionDto | UpdateTransactionDto]
  cancel: []
}>()

// Form data
const form = reactive({
  type: props.transaction?.type || 'expense' as TransactionType,
  amount: props.transaction?.amount || 0,
  date: props.transaction?.date || formatDateForInput(new Date()),
  account_id: props.transaction?.account_id || '',
  category_id: props.transaction?.category_id || '',
  title: props.transaction?.title || '',
  description: props.transaction?.description || '',
  tags: props.transaction?.tags?.join(', ') || ''
})

// Validation errors
const errors = reactive({
  type: '',
  amount: '',
  date: '',
  account_id: '',
  category_id: ''
})

const isEditMode = computed(() => !!props.transaction)

// Get currency from selected account
const selectedAccountCurrency = computed(() => {
  const account = props.accounts.find(a => a.id === form.account_id)
  return account?.currency || 'USD'
})

// Watch type to reset category_id when type changes
watch(() => form.type, () => {
  form.category_id = ''
})

function validateForm(): boolean {
  let isValid = true

  // Validate type
  if (!form.type) {
    errors.type = 'Debes seleccionar el tipo de transacción'
    isValid = false
  } else {
    errors.type = ''
  }

  // Validate amount
  const amountValidation = positiveNumber(form.amount)
  if (amountValidation !== true) {
    errors.amount = amountValidation as string
    isValid = false
  } else {
    errors.amount = ''
  }

  // Validate date
  if (!form.date) {
    errors.date = 'Debes seleccionar una fecha'
    isValid = false
  } else {
    errors.date = ''
  }

  // Validate account_id
  if (!form.account_id) {
    errors.account_id = 'Debes seleccionar una cuenta'
    isValid = false
  } else {
    errors.account_id = ''
  }

  // Validate category_id
  if (!form.category_id) {
    errors.category_id = 'Debes seleccionar una categoría'
    isValid = false
  } else {
    errors.category_id = ''
  }

  return isValid
}

function handleSubmit() {
  if (!validateForm()) return

  const data: CreateTransactionDto | UpdateTransactionDto = {
    type: form.type,
    amount: form.amount,
    date: form.date,
    account_id: form.account_id,
    category_id: form.category_id,
    title: form.title.trim() || undefined,
    description: form.description.trim() || undefined,
    tags: form.tags
      ? form.tags.split(',').map(t => t.trim()).filter(t => t.length > 0)
      : []
  }

  emit('submit', data)
}
</script>

<template>
  <form @submit.prevent="handleSubmit" class="space-y-4">
    <!-- Tipo -->
    <BaseSelect
      v-model="form.type"
      label="Tipo"
      :options="TRANSACTION_TYPES"
      :error="errors.type"
      required
    />

    <!-- Monto -->
    <AmountInput
      v-model="form.amount"
      label="Monto"
      :currency="selectedAccountCurrency"
      placeholder="0.00"
      :error="errors.amount"
      required
    />

    <!-- Fecha -->
    <DatePicker
      v-model="form.date"
      label="Fecha"
      :error="errors.date"
      :max="formatDateForInput(new Date())"
      required
    />

    <!-- Cuenta -->
    <AccountSelect
      v-model="form.account_id"
      :accounts="accounts"
      :error="errors.account_id"
      required
    />

    <!-- Categoría (filtered by type) -->
    <CategorySelect
      v-model="form.category_id"
      :categories="categories"
      :filter-type="form.type"
      :error="errors.category_id"
      required
    />

    <!-- Título -->
    <BaseInput
      v-model="form.title"
      label="Título (opcional)"
      placeholder="Ej: Compra supermercado"
    />

    <!-- Descripción -->
    <BaseInput
      v-model="form.description"
      label="Descripción (opcional)"
      placeholder="Detalles adicionales"
    />

    <!-- Tags -->
    <BaseInput
      v-model="form.tags"
      label="Etiquetas (opcional)"
      placeholder="comida, semanal (separadas por comas)"
      helper-text="Separadas por comas"
    />

    <!-- Actions -->
    <div class="flex gap-3 pt-4 flex-col md:flex-row">
      <BaseButton
        type="submit"
        variant="primary"
        :loading="loading"
        full-width
      >
        {{ isEditMode ? 'Actualizar' : 'Crear' }} transacción
      </BaseButton>
      <BaseButton
        type="button"
        variant="ghost"
        :disabled="loading"
        full-width
        @click="emit('cancel')"
      >
        Cancelar
      </BaseButton>
    </div>
  </form>
</template>
