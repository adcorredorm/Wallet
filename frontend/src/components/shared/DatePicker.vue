<script setup lang="ts">
/**
 * Date Picker Component
 *
 * Why native input[type=date]?
 * - Better mobile UX (native keyboard/picker)
 * - Accessibility built-in
 * - No heavy date picker library needed
 * - Works offline
 *
 * Custom date pickers are usually worse on mobile than native
 */

import { computed } from 'vue'
import { formatDateForInput } from '@/utils/formatters'

interface Props {
  modelValue: string // ISO date string YYYY-MM-DD
  label?: string
  error?: string
  required?: boolean
  disabled?: boolean
  min?: string
  max?: string
}

const props = withDefaults(defineProps<Props>(), {
  required: false,
  disabled: false
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const inputValue = computed({
  get: () => props.modelValue,
  set: (value: string) => emit('update:modelValue', value)
})
</script>

<template>
  <div class="w-full">
    <!-- Label -->
    <label v-if="label" class="label">
      {{ label }}
      <span v-if="required" class="text-accent-red ml-1">*</span>
    </label>

    <!-- Native date input (best mobile UX) -->
    <input
      v-model="inputValue"
      type="date"
      :disabled="disabled"
      :min="min"
      :max="max"
      :class="[
        'input',
        {
          'border-accent-red': error,
          'bg-dark-bg-tertiary/50 cursor-not-allowed': disabled
        }
      ]"
    />

    <!-- Error message -->
    <p v-if="error" class="mt-1 text-sm text-accent-red">
      {{ error }}
    </p>
  </div>
</template>
