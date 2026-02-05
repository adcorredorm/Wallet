<script setup lang="ts">
/**
 * Base Input Component
 *
 * Why v-model support?
 * - Two-way binding for reactive forms
 * - Validation error display
 * - Label and helper text built-in
 *
 * Mobile considerations:
 * - Touch-friendly height (44px min)
 * - Appropriate keyboard types for mobile
 * - Clear visual feedback on focus
 */

interface Props {
  modelValue: string | number
  label?: string
  type?: string
  placeholder?: string
  error?: string
  helperText?: string
  required?: boolean
  disabled?: boolean
  readonly?: boolean
  autocomplete?: string
}

const props = withDefaults(defineProps<Props>(), {
  type: 'text',
  required: false,
  disabled: false,
  readonly: false
})

const emit = defineEmits<{
  'update:modelValue': [value: string | number]
}>()

function handleInput(event: Event) {
  const target = event.target as HTMLInputElement
  const value = props.type === 'number' ? Number(target.value) : target.value
  emit('update:modelValue', value)
}
</script>

<template>
  <div class="w-full">
    <!-- Label -->
    <label v-if="label" class="label">
      {{ label }}
      <span v-if="required" class="text-accent-red ml-1">*</span>
    </label>

    <!-- Input field -->
    <input
      :type="type"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      :readonly="readonly"
      :autocomplete="autocomplete"
      :class="[
        'input',
        {
          'border-accent-red': error,
          'bg-dark-bg-tertiary/50 cursor-not-allowed': disabled
        }
      ]"
      @input="handleInput"
    />

    <!-- Helper text or error -->
    <p v-if="error" class="mt-1 text-sm text-accent-red">
      {{ error }}
    </p>
    <p v-else-if="helperText" class="mt-1 text-sm text-dark-text-tertiary">
      {{ helperText }}
    </p>
  </div>
</template>
