<script setup lang="ts">
/**
 * ExchangeRateInput
 *
 * Two linked plain-text fields showing the same exchange rate in both directions:
 *
 *   Field 1: quoteCurrency per 1 baseCurrency  (canonical modelValue)
 *            e.g. "COP por 1 USD" = 4200
 *
 *   Field 2: baseCurrency per 1 quoteCurrency  (inverse)
 *            e.g. "USD por 1 COP" = 0.000238...
 *
 * Anti-loop design:
 *   - Each @input handler updates the OTHER field via direct assignment — not
 *     via a watcher between the two ref() values. This breaks the reactive
 *     cycle completely: rate1Display changing never triggers a watcher that
 *     writes to rate2Display and back.
 *   - The `isExternalUpdate` plain boolean prevents the prop watcher from
 *     re-triggering when the component itself emits the canonical rate and the
 *     parent echoes it back as the next modelValue.
 *
 * Why :readonly and not :disabled?
 *   The spec requires readonly so the field still shows its value clearly
 *   but is not editable. :disabled visually greys out content more aggressively
 *   and prevents copying the value on mobile.
 */

import { ref, watch } from 'vue'

interface Props {
  modelValue: number
  baseCurrency: string
  quoteCurrency: string
  disabled?: boolean
  error?: string
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: number]
}>()

// ─── Display state ───────────────────────────────────────────────────────────
// Plain string refs — we own the text completely, same pattern as AmountInput.
const rate1Display = ref('')
const rate2Display = ref('')

// ─── External update guard ────────────────────────────────────────────────────
// Plain boolean (not reactive): used only as a one-tick flag to stop the prop
// watcher from re-running when *we* are the ones that emitted the new value.
let isExternalUpdate = false

// ─── Formatting ───────────────────────────────────────────────────────────────
/**
 * Formats a rate for display.
 * - toFixed(10) gives us 10 decimal places of precision (important for tiny
 *   rates like 1/4200 = 0.0002380952380952)
 * - parseFloat().toString() strips trailing zeros natively without regex
 * - No thousands separators — rates are ratios, not monetary amounts
 */
function formatRateForDisplay(value: number): string {
  return parseFloat(value.toFixed(10)).toString()
}

// ─── Prop watcher (external parent updates) ──────────────────────────────────
watch(
  () => props.modelValue,
  (newVal) => {
    if (isExternalUpdate) return
    isExternalUpdate = true
    if (newVal > 0) {
      rate1Display.value = formatRateForDisplay(newVal)
      rate2Display.value = formatRateForDisplay(1 / newVal)
    } else {
      rate1Display.value = ''
      rate2Display.value = ''
    }
    isExternalUpdate = false
  },
  { immediate: true }
)

// ─── Input handlers ───────────────────────────────────────────────────────────

/**
 * Field 1: quoteCurrency per 1 baseCurrency (canonical rate)
 * Emits the parsed value and updates Field 2 with its inverse.
 */
function handleRate1Input(event: Event) {
  const raw = (event.target as HTMLInputElement).value
  rate1Display.value = raw
  const parsed = parseFloat(raw)
  if (!parsed || isNaN(parsed) || parsed <= 0) {
    rate2Display.value = ''
    return
  }
  rate2Display.value = formatRateForDisplay(1 / parsed)
  isExternalUpdate = true
  emit('update:modelValue', parsed)
  isExternalUpdate = false
}

/**
 * Field 2: baseCurrency per 1 quoteCurrency (inverse display)
 * Emits 1/parsed as the canonical rate and updates Field 1.
 */
function handleRate2Input(event: Event) {
  const raw = (event.target as HTMLInputElement).value
  rate2Display.value = raw
  const parsed = parseFloat(raw)
  if (!parsed || isNaN(parsed) || parsed <= 0) {
    rate1Display.value = ''
    return
  }
  const canonical = 1 / parsed
  rate1Display.value = formatRateForDisplay(canonical)
  isExternalUpdate = true
  emit('update:modelValue', canonical)
  isExternalUpdate = false
}
</script>

<template>
  <div class="w-full space-y-1">
    <div class="grid grid-cols-2 gap-3">
      <!-- Field 1: quoteCurrency per 1 baseCurrency (canonical) -->
      <div>
        <label class="label text-xs">{{ quoteCurrency }} por 1 {{ baseCurrency }}</label>
        <input
          type="text"
          inputmode="decimal"
          :value="rate1Display"
          :readonly="disabled"
          :class="['input', { 'opacity-50 cursor-not-allowed': disabled }]"
          autocomplete="off"
          @input="handleRate1Input"
        />
      </div>

      <!-- Field 2: baseCurrency per 1 quoteCurrency (inverse) -->
      <div>
        <label class="label text-xs">{{ baseCurrency }} por 1 {{ quoteCurrency }}</label>
        <input
          type="text"
          inputmode="decimal"
          :value="rate2Display"
          :readonly="disabled"
          :class="['input', { 'opacity-50 cursor-not-allowed': disabled }]"
          autocomplete="off"
          @input="handleRate2Input"
        />
      </div>
    </div>

    <!-- Error message -->
    <p v-if="error" class="text-sm text-accent-red">{{ error }}</p>
  </div>
</template>
