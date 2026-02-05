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
  cuenta_origen_id: props.transfer?.cuenta_origen_id || '',
  cuenta_destino_id: props.transfer?.cuenta_destino_id || '',
  monto: props.transfer?.monto || 0,
  fecha: props.transfer?.fecha || formatDateForInput(new Date()),
  titulo: props.transfer?.titulo || '',
  descripcion: props.transfer?.descripcion || '',
  tags: props.transfer?.tags?.join(', ') || ''
})

// Validation errors
const errors = reactive({
  cuenta_origen_id: '',
  cuenta_destino_id: '',
  monto: '',
  fecha: ''
})

const isEditMode = computed(() => !!props.transfer)

// Get currency from origin account
const originAccountCurrency = computed(() => {
  const account = props.accounts.find(a => a.id === form.cuenta_origen_id)
  return account?.divisa || 'USD'
})

function validateForm(): boolean {
  let isValid = true

  // Validate cuenta_origen_id
  if (!form.cuenta_origen_id) {
    errors.cuenta_origen_id = 'Debes seleccionar una cuenta de origen'
    isValid = false
  } else {
    errors.cuenta_origen_id = ''
  }

  // Validate cuenta_destino_id
  if (!form.cuenta_destino_id) {
    errors.cuenta_destino_id = 'Debes seleccionar una cuenta de destino'
    isValid = false
  } else if (form.cuenta_destino_id === form.cuenta_origen_id) {
    errors.cuenta_destino_id = 'La cuenta de destino debe ser diferente al origen'
    isValid = false
  } else {
    errors.cuenta_destino_id = ''
  }

  // Validate monto
  const montoValidation = positiveNumber(form.monto)
  if (montoValidation !== true) {
    errors.monto = montoValidation as string
    isValid = false
  } else {
    errors.monto = ''
  }

  // Validate fecha
  if (!form.fecha) {
    errors.fecha = 'Debes seleccionar una fecha'
    isValid = false
  } else {
    errors.fecha = ''
  }

  return isValid
}

function handleSubmit() {
  if (!validateForm()) return

  const data: CreateTransferDto | UpdateTransferDto = {
    cuenta_origen_id: form.cuenta_origen_id,
    cuenta_destino_id: form.cuenta_destino_id,
    monto: form.monto,
    fecha: form.fecha,
    titulo: form.titulo.trim() || undefined,
    descripcion: form.descripcion.trim() || undefined,
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
      v-model="form.cuenta_origen_id"
      :accounts="accounts"
      label="Cuenta de origen"
      placeholder="Selecciona cuenta origen"
      :error="errors.cuenta_origen_id"
      required
    />

    <!-- Cuenta destino -->
    <AccountSelect
      v-model="form.cuenta_destino_id"
      :accounts="accounts"
      label="Cuenta de destino"
      placeholder="Selecciona cuenta destino"
      :filter-out-account-id="form.cuenta_origen_id"
      :error="errors.cuenta_destino_id"
      required
    />

    <!-- Monto -->
    <AmountInput
      v-model="form.monto"
      label="Monto"
      :currency="originAccountCurrency"
      placeholder="0.00"
      :error="errors.monto"
      required
    />

    <!-- Fecha -->
    <DatePicker
      v-model="form.fecha"
      label="Fecha"
      :error="errors.fecha"
      :max="formatDateForInput(new Date())"
      required
    />

    <!-- Título -->
    <BaseInput
      v-model="form.titulo"
      label="Título (opcional)"
      placeholder="Ej: Transferencia a ahorros"
    />

    <!-- Descripción -->
    <BaseInput
      v-model="form.descripcion"
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
