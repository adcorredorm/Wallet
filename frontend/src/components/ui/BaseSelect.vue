<script setup lang="ts">
/**
 * Base Select Component
 *
 * Why a custom select?
 * - Consistent styling with other inputs
 * - Support for option objects with labels
 * - Error state display
 *
 * Mobile considerations:
 * - Native select on mobile (better UX than custom)
 * - Touch-friendly height
 */

interface Option {
  value: string | number
  label: string
  disabled?: boolean
}

interface OptionGroup {
  label: string
  options: readonly Option[]
}

interface Props {
  modelValue: string | number
  label?: string
  options?: readonly Option[]
  optionGroups?: OptionGroup[]
  placeholder?: string
  error?: string
  required?: boolean
  disabled?: boolean
}

withDefaults(defineProps<Props>(), {
  required: false,
  disabled: false
})

const emit = defineEmits<{
  'update:modelValue': [value: string | number]
}>()

function handleChange(event: Event) {
  const target = event.target as HTMLSelectElement
  emit('update:modelValue', target.value)
}
</script>

<template>
  <div class="w-full">
    <!-- Label -->
    <label v-if="label" class="label">
      {{ label }}
      <span v-if="required" class="text-accent-red ml-1">*</span>
    </label>

    <!-- Select field -->
    <select
      :value="modelValue"
      :disabled="disabled"
      :class="[
        'select',
        {
          'border-accent-red': error,
          'bg-dark-bg-tertiary/50 cursor-not-allowed': disabled
        }
      ]"
      @change="handleChange"
    >
      <option v-if="placeholder" value="" disabled>
        {{ placeholder }}
      </option>

      <!-- Grouped options (when optionGroups is provided) -->
      <template v-if="optionGroups && optionGroups.length > 0">
        <optgroup
          v-for="group in optionGroups"
          :key="group.label"
          :label="group.label"
        >
          <option
            v-for="option in group.options"
            :key="option.value"
            :value="option.value"
            :disabled="option.disabled"
          >
            {{ option.label }}
          </option>
        </optgroup>
      </template>

      <!-- Flat options (default, backward-compatible) -->
      <template v-if="options && options.length > 0">
        <option
          v-for="option in options"
          :key="option.value"
          :value="option.value"
          :disabled="option.disabled"
        >
          {{ option.label }}
        </option>
      </template>
    </select>

    <!-- Error message -->
    <p v-if="error" class="mt-1 text-sm text-accent-red">
      {{ error }}
    </p>
  </div>
</template>
