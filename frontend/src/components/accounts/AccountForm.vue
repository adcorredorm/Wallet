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
import { useSettingsStore } from '@/stores/settings'
import type { Account, CreateAccountDto, UpdateAccountDto, AccountType } from '@/types'

const settingsStore = useSettingsStore()

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
  name: props.account?.name || '',
  type: props.account?.type || '' as AccountType,
  currency: props.account?.currency || settingsStore.primaryCurrency,
  description: props.account?.description || '',
  tags: props.account?.tags?.join(', ') || ''
})

// Validation errors
const errors = reactive({
  name: '',
  type: '',
  currency: ''
})

const isEditMode = computed(() => !!props.account)

function validateForm(): boolean {
  let isValid = true

  // Validate name
  const nameValidation = required(form.name) && minLength(2)(form.name) && maxLength(100)(form.name)
  if (nameValidation !== true) {
    errors.name = nameValidation as string
    isValid = false
  } else {
    errors.name = ''
  }

  // Validate type
  if (!form.type) {
    errors.type = 'Debes seleccionar un tipo de cuenta'
    isValid = false
  } else {
    errors.type = ''
  }

  // Validate currency
  const currencyValidation = currencyCode(form.currency)
  if (currencyValidation !== true) {
    errors.currency = currencyValidation as string
    isValid = false
  } else {
    errors.currency = ''
  }

  return isValid
}

function handleSubmit() {
  if (!validateForm()) return

  const data: CreateAccountDto | UpdateAccountDto = {
    name: form.name.trim(),
    type: form.type,
    currency: form.currency.toUpperCase(),
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
    <!-- Nombre -->
    <BaseInput
      v-model="form.name"
      label="Nombre de la cuenta"
      placeholder="Ej: Cuenta Corriente"
      :error="errors.name"
      required
    />

    <!-- Tipo -->
    <BaseSelect
      v-model="form.type"
      label="Tipo de cuenta"
      :options="ACCOUNT_TYPES"
      placeholder="Selecciona un tipo"
      :error="errors.type"
      required
    />

    <!-- Divisa -->
    <BaseSelect
      v-model="form.currency"
      label="Divisa"
      :options="CURRENCIES"
      :error="errors.currency"
      required
    />

    <!-- Descripción -->
    <BaseInput
      v-model="form.description"
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
