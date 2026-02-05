<script setup lang="ts">
/**
 * Category Select Component
 *
 * Dropdown to select a category (for transactions)
 * Filters by type (ingreso/gasto) automatically
 */

import { computed } from 'vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import type { Category, CategoryType } from '@/types'

interface Props {
  modelValue: string
  categories: Category[]
  filterType?: CategoryType // Filter categories by type
  label?: string
  placeholder?: string
  error?: string
  required?: boolean
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  label: 'Categoría',
  placeholder: 'Selecciona una categoría',
  required: false,
  disabled: false
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const options = computed(() => {
  return props.categories
    .filter(category => {
      if (!props.filterType) return true
      return category.tipo === props.filterType || category.tipo === 'ambos'
    })
    .map(category => ({
      value: category.id,
      label: `${category.icono || ''} ${category.nombre}`.trim()
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
