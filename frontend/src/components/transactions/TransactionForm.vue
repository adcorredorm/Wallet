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
  tipo: props.transaction?.tipo || 'gasto' as TransactionType,
  monto: props.transaction?.monto || 0,
  fecha: props.transaction?.fecha || formatDateForInput(new Date()),
  cuenta_id: props.transaction?.cuenta_id || '',
  categoria_id: props.transaction?.categoria_id || '',
  titulo: props.transaction?.titulo || '',
  descripcion: props.transaction?.descripcion || '',
  tags: props.transaction?.tags?.join(', ') || ''
})

// Validation errors
const errors = reactive({
  tipo: '',
  monto: '',
  fecha: '',
  cuenta_id: '',
  categoria_id: ''
})

const isEditMode = computed(() => !!props.transaction)

// Get currency from selected account
const selectedAccountCurrency = computed(() => {
  const account = props.accounts.find(a => a.id === form.cuenta_id)
  return account?.divisa || 'USD'
})

// Watch tipo to reset category_id when type changes
watch(() => form.tipo, () => {
  form.categoria_id = ''
})

function validateForm(): boolean {
  let isValid = true

  // Validate tipo
  if (!form.tipo) {
    errors.tipo = 'Debes seleccionar el tipo de transacción'
    isValid = false
  } else {
    errors.tipo = ''
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

  // Validate cuenta_id
  if (!form.cuenta_id) {
    errors.cuenta_id = 'Debes seleccionar una cuenta'
    isValid = false
  } else {
    errors.cuenta_id = ''
  }

  // Validate categoria_id
  if (!form.categoria_id) {
    errors.categoria_id = 'Debes seleccionar una categoría'
    isValid = false
  } else {
    errors.categoria_id = ''
  }

  return isValid
}

function handleSubmit() {
  if (!validateForm()) return

  const data: CreateTransactionDto | UpdateTransactionDto = {
    tipo: form.tipo,
    monto: form.monto,
    fecha: form.fecha,
    cuenta_id: form.cuenta_id,
    categoria_id: form.categoria_id,
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
    <!-- Tipo -->
    <BaseSelect
      v-model="form.tipo"
      label="Tipo"
      :options="TRANSACTION_TYPES"
      :error="errors.tipo"
      required
    />

    <!-- Monto -->
    <AmountInput
      v-model="form.monto"
      label="Monto"
      :currency="selectedAccountCurrency"
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

    <!-- Cuenta -->
    <AccountSelect
      v-model="form.cuenta_id"
      :accounts="accounts"
      :error="errors.cuenta_id"
      required
    />

    <!-- Categoría (filtered by tipo) -->
    <CategorySelect
      v-model="form.categoria_id"
      :categories="categories"
      :filter-type="form.tipo"
      :error="errors.categoria_id"
      required
    />

    <!-- Título -->
    <BaseInput
      v-model="form.titulo"
      label="Título (opcional)"
      placeholder="Ej: Compra supermercado"
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
