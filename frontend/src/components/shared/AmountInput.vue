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

import { ref, watch, computed, nextTick, useTemplateRef } from 'vue'
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

const inputEl = useTemplateRef<HTMLInputElement>('input')
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

/**
 * findPositionAfterNSignificant
 *
 * Walks `str` counting chars that are a digit (0-9) or comma. When the count
 * reaches `n`, returns `i + 1` (the index after that character). This maps a
 * "raw offset" (position in terms of significant chars only, ignoring dot
 * thousand-separators) back to an absolute index in the formatted string.
 *
 * Why comma counts as significant here?
 * The Spanish decimal separator is ','. When the user positions the cursor
 * after the comma, `rawOffset` will have counted the comma itself — so when
 * we reconstruct the position in the newly formatted string we must count the
 * comma too, otherwise the cursor would land one position early.
 */
function findPositionAfterNSignificant(str: string, n: number): number {
  if (n <= 0) return 0
  let count = 0
  for (let i = 0; i < str.length; i++) {
    const ch = str[i]
    if ((ch >= '0' && ch <= '9') || ch === ',') {
      count++
      if (count === n) return i + 1
    }
  }
  return str.length
}

function handleInput(event: Event) {
  const el = event.target as HTMLInputElement
  const rawCursor = el.selectionStart ?? el.value.length

  // Count significant chars (digits + comma) before cursor in the NEW input value.
  // This avoids indexing the post-insertion cursor into the old pre-insertion display
  // string, which over-counts thousand-separator dots when a digit crosses a boundary.
  const rawOffset = (el.value.slice(0, rawCursor).match(/[\d,]/g) ?? []).length

  // Keep only digits and the decimal comma — discard everything else the user
  // might have pasted (spaces, currency symbols, stray dots, etc.)
  const stripped = el.value.replace(/[^\d,]/g, '')

  if (!stripped) {
    displayValue.value = ''
    emit('update:modelValue', 0)
    return
  }

  // Partial decimal: user just typed ',' at the end. Do NOT call formatNumber
  // yet because it would append ",00" (or more zeros for crypto). Instead,
  // format only the integer part and append a bare comma so the cursor stays
  // in the right place for the upcoming decimal digits.
  if (stripped.endsWith(',')) {
    const integerPart = stripped.slice(0, -1).replace(/,/g, '')
    const integerNum = parseFloat(integerPart) || 0
    const formattedInt = formatNumber(integerNum, 0)
    displayValue.value = formattedInt + ','
    emit('update:modelValue', integerNum)
    return
  }

  const numericValue = parseFormattedNumber(stripped)
  // Note: parseFormattedNumber returns 0 (not NaN) for invalid input due to `|| 0` fallback.
  // The isNaN guard below is a defensive belt-and-suspenders check in case that contract changes.
  if (isNaN(numericValue)) {
    displayValue.value = stripped
    return
  }

  const newDisplay = formatForDisplay(numericValue)
  displayValue.value = newDisplay
  emit('update:modelValue', numericValue)

  // Restore cursor to the equivalent position in the newly formatted string.
  // We use nextTick because Vue hasn't updated the DOM yet — the input's value
  // will reflect `newDisplay` only after the reactive flush.
  const newPos = findPositionAfterNSignificant(newDisplay, rawOffset)
  nextTick(() => {
    // Only restore cursor if the input is still focused. Calling setSelectionRange
    // on a blurred input can trigger side effects in some browsers (e.g. spurious
    // input events or DOM value resets) that corrupt the display value.
    if (document.activeElement === inputEl.value) {
      inputEl.value?.setSelectionRange(newPos, newPos)
    }
  })
}

function handleBlur() {
  // Remove any dangling trailing comma the user left (e.g., "5.000,")
  const cleaned = displayValue.value.replace(/,$/, '')
  const numericValue = parseFormattedNumber(cleaned)
  if (!isNaN(numericValue) && numericValue !== 0) {
    displayValue.value = formatForDisplay(numericValue)
  } else {
    // Clear on zero or unparseable: amounts are always positive per arch rules
    displayValue.value = ''
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
        ref="input"
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
