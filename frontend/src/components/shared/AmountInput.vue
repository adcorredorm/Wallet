<script setup lang="ts">
/**
 * Amount Input Component
 *
 * Why specialized amount input?
 * - Currency formatting while typing
 * - Numeric keyboard on mobile
 * - Decimal handling (2 decimal places)
 * - Visual feedback for positive/negative
 */

import { ref, watch, computed } from 'vue'
import { formatNumber, parseFormattedNumber } from '@/utils/formatters'
import { SUPPORTED_CURRENCIES } from '@/utils/constants'

// Build a lookup map once at module level — no reactive overhead needed
const CURRENCY_SYMBOL_MAP: Record<string, string> = Object.fromEntries(
  SUPPORTED_CURRENCIES.map(c => [c.code, c.symbol])
)

const CRYPTO_CURRENCIES = new Set(['BTC', 'ETH'])

interface Props {
  modelValue: number
  label?: string
  currency?: string
  placeholder?: string
  error?: string
  required?: boolean
  disabled?: boolean
  min?: number
  max?: number
}

const props = withDefaults(defineProps<Props>(), {
  currency: 'USD',
  min: 0,
  required: false,
  disabled: false
})

const emit = defineEmits<{
  'update:modelValue': [value: number]
}>()

const displayValue = ref('')

// Crypto uses up to 8 decimals; fiat uses 2
const decimals = computed(() =>
  CRYPTO_CURRENCIES.has(props.currency?.toUpperCase() ?? '') ? 8 : 2
)

// Format a number for display, trimming trailing zeros after the decimal
function formatForDisplay(value: number): string {
  const formatted = formatNumber(value, decimals.value)
  // Strip trailing zeros after decimal comma (Spanish format uses ',')
  // "1,00000000" → "1", "0,00100000" → "0,001", "1,50" → "1,5"
  return formatted.replace(/,(\d*?)0+$/, (_, digits) => digits ? `,${digits}` : '').replace(/,$/, '')
}

// Initialize display value
watch(() => props.modelValue, (value) => {
  if (value !== parseFormattedNumber(displayValue.value)) {
    displayValue.value = value ? formatForDisplay(value) : ''
  }
}, { immediate: true })

function handleInput(event: Event) {
  const target = event.target as HTMLInputElement
  let value = target.value

  // Remove non-numeric characters except comma and dot
  value = value.replace(/[^\d,.-]/g, '')

  // Update display
  displayValue.value = value

  // Parse and emit numeric value
  const numericValue = parseFormattedNumber(value)
  if (!isNaN(numericValue)) {
    emit('update:modelValue', numericValue)
  }
}

function handleBlur() {
  const numericValue = parseFormattedNumber(displayValue.value)
  if (!isNaN(numericValue)) {
    displayValue.value = formatForDisplay(numericValue)
  }
}
</script>

<template>
  <div class="w-full">
    <!-- Label -->
    <label v-if="label" class="label">
      {{ label }}
      <span v-if="required" class="text-accent-red ml-1">*</span>
    </label>

    <!-- Input with currency prefix -->
    <div class="relative">
      <span class="absolute left-4 top-1/2 -translate-y-1/2 text-dark-text-secondary">
        {{ CURRENCY_SYMBOL_MAP[currency] ?? currency }}
      </span>
      <input
        type="text"
        inputmode="decimal"
        :value="displayValue"
        :placeholder="placeholder"
        :disabled="disabled"
        :class="[
          'input pl-10',
          {
            'border-accent-red': error,
            'bg-dark-bg-tertiary/50 cursor-not-allowed': disabled
          }
        ]"
        @input="handleInput"
        @blur="handleBlur"
      />
    </div>

    <!-- Error message -->
    <p v-if="error" class="mt-1 text-sm text-accent-red">
      {{ error }}
    </p>
  </div>
</template>
