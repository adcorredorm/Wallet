<script setup lang="ts">
/**
 * Account Select Component
 *
 * Dropdown to select an account (for transactions/transfers)
 * Shows account name, type, and currency
 */

import { computed } from 'vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import type { Account } from '@/types'

interface Props {
  modelValue: string
  accounts: Account[]
  label?: string
  placeholder?: string
  error?: string
  required?: boolean
  disabled?: boolean
  filterOutAccountId?: string // For transfers, exclude one account
}

const props = withDefaults(defineProps<Props>(), {
  label: 'Cuenta',
  placeholder: 'Selecciona una cuenta',
  required: false,
  disabled: false
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const options = computed(() => {
  return props.accounts
    .filter(account => {
      // Filter out the excluded account (for transfers)
      if (props.filterOutAccountId && account.id === props.filterOutAccountId) {
        return false
      }
      return account.active
    })
    .map(account => ({
      value: account.id,
      label: `${account.name} (${account.currency})`
    }))
})
</script>

<template>
  <BaseSelect
    :model-value="modelValue"
    :label="label"
    :options="options"
    :placeholder="placeholder"
    :error="error"
    :required="required"
    :disabled="disabled"
    @update:model-value="emit('update:modelValue', $event)"
  />
</template>
