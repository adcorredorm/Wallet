<script setup lang="ts">
/**
 * Transfer Form Component
 *
 * Form for creating/editing transfers between accounts
 */

import { reactive, computed } from 'vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import AmountInput from '@/components/shared/AmountInput.vue'
import DatePicker from '@/components/shared/DatePicker.vue'
import AccountSelect from '@/components/accounts/AccountSelect.vue'
import { positiveNumber } from '@/utils/validators'
import { formatDateForInput } from '@/utils/formatters'
import type { Transfer, CreateTransferDto, UpdateTransferDto, Account } from '@/types'

interface Props {
  transfer?: Transfer
  accounts: Account[]
  loading?: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  submit: [data: CreateTransferDto | UpdateTransferDto]
  cancel: []
}>()

// Form data
const form = reactive({
  source_account_id: props.transfer?.source_account_id || '',
  destination_account_id: props.transfer?.destination_account_id || '',
  amount: props.transfer?.amount || 0,
  date: props.transfer?.date || formatDateForInput(new Date()),
  title: props.transfer?.title || '',
  description: props.transfer?.description || '',
  tags: props.transfer?.tags?.join(', ') || ''
})

// Validation errors
const errors = reactive({
  source_account_id: '',
  destination_account_id: '',
  amount: '',
  date: ''
})

const isEditMode = computed(() => !!props.transfer)

// Get currency from origin account
const originAccountCurrency = computed(() => {
  const account = props.accounts.find(a => a.id === form.source_account_id)
  return account?.currency || 'USD'
})

function validateForm(): boolean {
  let isValid = true

  // Validate source_account_id
  if (!form.source_account_id) {
    errors.source_account_id = 'Debes seleccionar una cuenta de origen'
    isValid = false
  } else {
    errors.source_account_id = ''
  }

  // Validate destination_account_id
  if (!form.destination_account_id) {
    errors.destination_account_id = 'Debes seleccionar una cuenta de destino'
    isValid = false
  } else if (form.destination_account_id === form.source_account_id) {
    errors.destination_account_id = 'La cuenta de destino debe ser diferente al origen'
    isValid = false
  } else {
    errors.destination_account_id = ''
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

  return isValid
}

function handleSubmit() {
  if (!validateForm()) return

  const data: CreateTransferDto | UpdateTransferDto = {
    source_account_id: form.source_account_id,
    destination_account_id: form.destination_account_id,
    amount: form.amount,
    date: form.date,
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
    <!-- Cuenta origen -->
    <AccountSelect
      v-model="form.source_account_id"
      :accounts="accounts"
      label="Cuenta de origen"
      placeholder="Selecciona cuenta origen"
      :error="errors.source_account_id"
      required
    />

    <!-- Cuenta destino -->
    <AccountSelect
      v-model="form.destination_account_id"
      :accounts="accounts"
      label="Cuenta de destino"
      placeholder="Selecciona cuenta destino"
      :filter-out-account-id="form.source_account_id"
      :error="errors.destination_account_id"
      required
    />

    <!-- Monto -->
    <AmountInput
      v-model="form.amount"
      label="Monto"
      :currency="originAccountCurrency"
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

    <!-- Título -->
    <BaseInput
      v-model="form.title"
      label="Título (opcional)"
      placeholder="Ej: Transferencia a ahorros"
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
      placeholder="ahorro, mensual (separadas por comas)"
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
        {{ isEditMode ? 'Actualizar' : 'Crear' }} transferencia
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
