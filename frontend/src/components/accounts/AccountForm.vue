<script setup lang="ts">
/**
 * Account Form Component
 *
 * Form for creating/editing accounts
 * Mobile-optimized with validation
 */

import { ref, reactive, computed } from 'vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import { ACCOUNT_TYPES, CURRENCIES } from '@/utils/constants'
import { required, minLength, maxLength, currencyCode } from '@/utils/validators'
import type { Account, CreateAccountDto, UpdateAccountDto, AccountType } from '@/types'

interface Props {
  account?: Account
  loading?: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  submit: [data: CreateAccountDto | UpdateAccountDto]
  cancel: []
}>()

// Form data
const form = reactive({
  nombre: props.account?.nombre || '',
  tipo: props.account?.tipo || '' as AccountType,
  divisa: props.account?.divisa || 'USD',
  descripcion: props.account?.descripcion || '',
  tags: props.account?.tags?.join(', ') || ''
})

// Validation errors
const errors = reactive({
  nombre: '',
  tipo: '',
  divisa: ''
})

const isEditMode = computed(() => !!props.account)

function validateForm(): boolean {
  let isValid = true

  // Validate nombre
  const nombreValidation = required(form.nombre) && minLength(2)(form.nombre) && maxLength(100)(form.nombre)
  if (nombreValidation !== true) {
    errors.nombre = nombreValidation as string
    isValid = false
  } else {
    errors.nombre = ''
  }

  // Validate tipo
  if (!form.tipo) {
    errors.tipo = 'Debes seleccionar un tipo de cuenta'
    isValid = false
  } else {
    errors.tipo = ''
  }

  // Validate divisa
  const divisaValidation = currencyCode(form.divisa)
  if (divisaValidation !== true) {
    errors.divisa = divisaValidation as string
    isValid = false
  } else {
    errors.divisa = ''
  }

  return isValid
}

function handleSubmit() {
  if (!validateForm()) return

  const data: CreateAccountDto | UpdateAccountDto = {
    nombre: form.nombre.trim(),
    tipo: form.tipo,
    divisa: form.divisa.toUpperCase(),
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
    <!-- Nombre -->
    <BaseInput
      v-model="form.nombre"
      label="Nombre de la cuenta"
      placeholder="Ej: Cuenta Corriente"
      :error="errors.nombre"
      required
    />

    <!-- Tipo -->
    <BaseSelect
      v-model="form.tipo"
      label="Tipo de cuenta"
      :options="ACCOUNT_TYPES"
      placeholder="Selecciona un tipo"
      :error="errors.tipo"
      required
    />

    <!-- Divisa -->
    <BaseSelect
      v-model="form.divisa"
      label="Divisa"
      :options="CURRENCIES"
      :error="errors.divisa"
      required
    />

    <!-- Descripción -->
    <BaseInput
      v-model="form.descripcion"
      label="Descripción (opcional)"
      placeholder="Información adicional sobre la cuenta"
      type="text"
    />

    <!-- Tags -->
    <BaseInput
      v-model="form.tags"
      label="Etiquetas (opcional)"
      placeholder="personal, banco1, ahorro (separadas por comas)"
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
        {{ isEditMode ? 'Actualizar' : 'Crear' }} cuenta
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
