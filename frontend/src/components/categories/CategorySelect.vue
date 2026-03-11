<script setup lang="ts">
/**
 * Category Select Component
 *
 * Dropdown to select a category (for transactions).
 * Uses categoryTree from the store to present a grouped hierarchy:
 * - Groups with children render as <optgroup> with parent as first selectable option
 * - Standalone categories render as flat options
 * Filters by type (ingreso/gasto) automatically.
 */

import { computed } from 'vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import { useCategoriesStore } from '@/stores'
import type { CategoryType } from '@/types'

interface Props {
  modelValue: string
  filterType?: CategoryType
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

const categoriesStore = useCategoriesStore()

/**
 * Helper: does a category match the filterType?
 * A category matches if no filter is set, or if its tipo equals the filter,
 * or if its tipo is 'ambos'.
 */
function matchesFilter(tipo: CategoryType): boolean {
  if (!props.filterType) return true
  return tipo === props.filterType || tipo === 'ambos'
}

/**
 * Build optionGroups for groups with children, and flat options for standalone.
 * Parents inside groups are selectable (they appear as the first option in the group).
 */
const optionGroups = computed(() => {
  const groups: { label: string; options: { value: string; label: string }[] }[] = []

  for (const group of categoriesStore.categoryTree) {
    if (group.children.length === 0) continue

    // Filter children
    const filteredChildren = group.children.filter(c => matchesFilter(c.tipo))
    const parentMatches = matchesFilter(group.parent.tipo)

    // Skip entire group if neither parent nor any child matches
    if (!parentMatches && filteredChildren.length === 0) continue

    const groupOptions: { value: string; label: string }[] = []

    // Add parent as first selectable option (only if it matches the filter)
    if (parentMatches) {
      groupOptions.push({
        value: group.parent.id,
        label: `${group.parent.icono ?? ''} ${group.parent.nombre}`.trim()
      })
    }

    // Add children
    for (const child of filteredChildren) {
      groupOptions.push({
        value: child.id,
        label: `${child.icono ?? ''} ${child.nombre}`.trim()
      })
    }

    if (groupOptions.length > 0) {
      groups.push({
        label: `${group.parent.icono ?? ''} ${group.parent.nombre}`.trim(),
        options: groupOptions
      })
    }
  }

  return groups
})

/**
 * Flat options for standalone categories (groups with no children).
 */
const flatOptions = computed(() => {
  return categoriesStore.categoryTree
    .filter(group => group.children.length === 0 && matchesFilter(group.parent.tipo))
    .map(group => ({
      value: group.parent.id,
      label: `${group.parent.icono ?? ''} ${group.parent.nombre}`.trim()
    }))
})
</script>

<template>
  <BaseSelect
    :model-value="modelValue"
    :label="label"
    :option-groups="optionGroups"
    :options="flatOptions"
    :placeholder="placeholder"
    :error="error"
    :required="required"
    :disabled="disabled"
    @update:model-value="emit('update:modelValue', String($event))"
  />
</template>
