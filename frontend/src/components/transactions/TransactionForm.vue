<script setup lang="ts">
/**
 * Transaction Form Component
 *
 * Form for creating/editing income/expense transactions.
 * Mobile-optimized with validation and optional FX (foreign currency) section.
 *
 * FX section appears when the user picks a foreign currency that differs from
 * the account's native currency. It exposes three interdependent fields:
 *   original_amount × exchange_rate = amount (account currency)
 * Editing any two recalculates the third automatically.
 */

import { ref, reactive, computed, watch, onMounted } from 'vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import AmountInput from '@/components/shared/AmountInput.vue'
import DatePicker from '@/components/shared/DatePicker.vue'
import AccountSelect from '@/components/accounts/AccountSelect.vue'
import CategorySelect from '@/components/categories/CategorySelect.vue'
import { TRANSACTION_TYPES, CURRENCIES } from '@/utils/constants'
import { required, positiveNumber } from '@/utils/validators'
import { formatDateForInput } from '@/utils/formatters'
import { useExchangeRatesStore } from '@/stores/exchangeRates'
import type { Transaction, CreateTransactionDto, UpdateTransactionDto, TransactionType, Account, Category } from '@/types'

interface Props {
  transaction?: Transaction
  accounts: Account[]
  categories: Category[]
  loading?: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  submit: [data: CreateTransactionDto | UpdateTransactionDto]
  cancel: []
}>()

const exchangeRatesStore = useExchangeRatesStore()

// ---------------------------------------------------------------------------
// Main form state
// ---------------------------------------------------------------------------

const form = reactive({
  type: props.transaction?.type || 'expense' as TransactionType,
  amount: props.transaction?.amount || 0,
  date: props.transaction?.date || formatDateForInput(new Date()),
  account_id: props.transaction?.account_id || '',
  category_id: props.transaction?.category_id || '',
  title: props.transaction?.title || '',
  description: props.transaction?.description || '',
  tags: props.transaction?.tags?.join(', ') || ''
})

// Validation errors
const errors = reactive({
  type: '',
  amount: '',
  date: '',
  account_id: '',
  category_id: ''
})

const isEditMode = computed(() => !!props.transaction)

// Currency from the selected account (falls back to 'USD' when no account is chosen yet)
const selectedAccountCurrency = computed(() => {
  const account = props.accounts.find(a => a.id === form.account_id)
  return account?.currency || 'USD'
})

// Watch type to reset category_id when type changes
watch(() => form.type, () => {
  form.category_id = ''
})

// ---------------------------------------------------------------------------
// FX (foreign currency) section state
// ---------------------------------------------------------------------------

// The currency the user is paying IN — null means same as account currency
const foreignCurrency = ref<string>('')

// Whether the collapsible FX section is visually expanded
const isFxSectionOpen = ref(false)

// ---------------------------------------------------------------------------
// Advanced options section state
// ---------------------------------------------------------------------------

// Whether the "Opciones avanzadas" collapsible block is expanded.
// Starts closed on new transactions; auto-opens when any optional field
// already has a value (edit mode or pre-populated form).
const isAdvancedOpen = ref(false)

// FX section field values — kept separate from `form` to isolate the reactive
// triangle logic. form.amount is always kept in sync with accountAmount when
// FX mode is active so existing validation and submission paths need no changes.
const originalAmount = ref<number | null>(null)
const accountAmount = ref<number | null>(null)
const exchangeRate = ref<number | null>(null)

// Tracks which field the user last touched to decide which one to recalculate.
// 'original' | 'account' | 'rate' | null (null = no user edit yet this session)
type FxField = 'original' | 'account' | 'rate'
const lastEditedFxField = ref<FxField | null>(null)

// True only when a foreign currency is selected AND it differs from the account currency
const fxActive = computed(() =>
  !!foreignCurrency.value && foreignCurrency.value !== selectedAccountCurrency.value
)

// Suggested rate from the cached exchange rates (foreign → account currency)
// Example: foreignCurrency = 'USD', accountCurrency = 'COP' → ~4200
const suggestedRate = computed(() =>
  fxActive.value
    ? exchangeRatesStore.getRate(foreignCurrency.value, selectedAccountCurrency.value)
    : null
)

// Shows a yellow warning when the user's entered rate deviates more than 10%
// from the cached market rate
const showRateAlert = computed(() => {
  if (!suggestedRate.value || !exchangeRate.value) return false
  const deviation = Math.abs(exchangeRate.value - suggestedRate.value) / suggestedRate.value
  return deviation > 0.10
})

// ---------------------------------------------------------------------------
// FX section watches: the "reactive triangle"
//
// Why three separate watchers instead of a single deep watch?
// Each watcher knows WHICH field was the source of the change. That lets us
// set lastEditedFxField and then compute the third field immediately, without
// guessing which two fields have "user" values and which one needs updating.
//
// Why the `lastEditedFxField !== 'X'` guards on each watcher?
// When watcher A recalculates field B, that triggers watcher B. Without the
// guard watcher B would then try to recalculate field A from B, causing an
// infinite feedback loop. The guard ensures each watcher only acts when the
// user — not another watcher — was the one who changed its own field.
// ---------------------------------------------------------------------------

watch(originalAmount, (val) => {
  if (lastEditedFxField.value === 'original') return // already handling
  lastEditedFxField.value = 'original'

  if (val !== null && exchangeRate.value !== null) {
    // User changed original_amount → recalculate account amount
    accountAmount.value = parseFloat((val * exchangeRate.value).toFixed(2))
    form.amount = accountAmount.value
  }

  lastEditedFxField.value = null
})

watch(accountAmount, (val) => {
  if (lastEditedFxField.value === 'account') return
  lastEditedFxField.value = 'account'

  if (val !== null) {
    form.amount = val
    if (originalAmount.value !== null && originalAmount.value !== 0) {
      // User changed account amount → recalculate exchange rate
      const rawRate = val / originalAmount.value
      exchangeRate.value = parseFloat(rawRate.toFixed(10))
    }
  }

  lastEditedFxField.value = null
})

watch(exchangeRate, (val) => {
  if (lastEditedFxField.value === 'rate') return
  lastEditedFxField.value = 'rate'

  if (val !== null && originalAmount.value !== null) {
    // User changed exchange_rate → recalculate account amount
    accountAmount.value = parseFloat((originalAmount.value * val).toFixed(2))
    form.amount = accountAmount.value
  }

  lastEditedFxField.value = null
})

// ---------------------------------------------------------------------------
// When the selected account changes, the FX section must reset because the
// account currency may have changed — an existing foreign currency choice
// might now be the same as the new account currency (making FX unnecessary)
// or the cached rate is now for a different base currency.
// ---------------------------------------------------------------------------
watch(() => form.account_id, () => {
  foreignCurrency.value = ''
  resetFxFields()
  isFxSectionOpen.value = false
})

// ---------------------------------------------------------------------------
// When the user selects / changes the foreign currency, pre-fill the exchange
// rate from the cached rates store so they don't have to type it manually.
// ---------------------------------------------------------------------------
watch(foreignCurrency, (currency) => {
  if (!currency || currency === selectedAccountCurrency.value) {
    // Deselected or same currency — collapse and clear
    resetFxFields()
    isFxSectionOpen.value = false
    return
  }

  // Auto-expand when a foreign currency is chosen
  isFxSectionOpen.value = true

  // Pre-fill the rate: how many account-currency units per 1 foreign unit
  const rate = exchangeRatesStore.getRate(currency, selectedAccountCurrency.value)
  if (rate !== null) {
    // Strip trailing zeros (per spec: parseFloat(n.toFixed(10)).toString())
    exchangeRate.value = parseFloat(parseFloat(rate.toFixed(10)).toString())
  } else {
    exchangeRate.value = null
  }
})

function resetFxFields() {
  originalAmount.value = null
  accountAmount.value = null
  exchangeRate.value = null
  lastEditedFxField.value = null
  // Restore form.amount to whatever was typed in the main amount field
  // before FX mode was activated. We cannot know that value here, so we
  // leave form.amount untouched — the user will re-enter it.
}

// Formats a rate number for display without trailing zeros and with up to
// 10 significant decimal digits (matches getRateDisplay() convention)
function formatRate(value: number | null): string {
  if (value === null) return ''
  return parseFloat(value.toFixed(10)).toString()
}

function handleRateInput(event: Event) {
  const raw = (event.target as HTMLInputElement).value
  const parsed = parseFloat(raw)
  exchangeRate.value = isNaN(parsed) ? null : parsed
}

function handleOriginalAmountInput(event: Event) {
  const raw = (event.target as HTMLInputElement).value
  const parsed = parseFloat(raw)
  originalAmount.value = isNaN(parsed) ? null : parsed
}

function handleAccountAmountInput(event: Event) {
  const raw = (event.target as HTMLInputElement).value
  const parsed = parseFloat(raw)
  accountAmount.value = isNaN(parsed) ? null : parsed
}

// Currency options for the foreign currency dropdown —
// filtered to exclude the account's own currency (same-currency FX is meaningless)
const foreignCurrencyOptions = computed(() => [
  { value: '', label: 'Sin moneda extranjera' },
  ...CURRENCIES.filter(c => c.value !== selectedAccountCurrency.value)
])

// ---------------------------------------------------------------------------
// Auto-open advanced section when optional fields already have values
// (e.g. editing an existing transaction).
// We run this once on mount so that the initial state of the reactive form
// is fully settled before we check.
// ---------------------------------------------------------------------------

onMounted(() => {
  const hasOptionalValues =
    !!form.tags ||
    !!foreignCurrency.value

  if (hasOptionalValues) {
    isAdvancedOpen.value = true
  }
})

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

function validateForm(): boolean {
  let isValid = true

  if (!form.type) {
    errors.type = 'Debes seleccionar el tipo de transacción'
    isValid = false
  } else {
    errors.type = ''
  }

  const amountValidation = positiveNumber(form.amount)
  if (amountValidation !== true) {
    errors.amount = amountValidation as string
    isValid = false
  } else {
    errors.amount = ''
  }

  if (!form.date) {
    errors.date = 'Debes seleccionar una fecha'
    isValid = false
  } else {
    errors.date = ''
  }

  if (!form.account_id) {
    errors.account_id = 'Debes seleccionar una cuenta'
    isValid = false
  } else {
    errors.account_id = ''
  }

  if (!form.category_id) {
    errors.category_id = 'Debes seleccionar una categoría'
    isValid = false
  } else {
    errors.category_id = ''
  }

  return isValid
}

// ---------------------------------------------------------------------------
// Submit
// ---------------------------------------------------------------------------

function handleSubmit() {
  if (!validateForm()) return

  const data: CreateTransactionDto | UpdateTransactionDto = {
    type: form.type,
    amount: form.amount,
    date: form.date,
    account_id: form.account_id,
    category_id: form.category_id,
    title: form.title.trim() || undefined,
    description: form.description.trim() || undefined,
    tags: form.tags
      ? form.tags.split(',').map(t => t.trim()).filter(t => t.length > 0)
      : [],
    // FX fields — null when no foreign currency is involved
    original_amount: fxActive.value ? (originalAmount.value ?? null) : null,
    original_currency: fxActive.value ? (foreignCurrency.value || null) : null,
    exchange_rate: fxActive.value ? (exchangeRate.value ?? null) : null
  }

  emit('submit', data)
}
</script>

<template>
  <form @submit.prevent="handleSubmit" class="space-y-4">
    <!-- Tipo -->
    <BaseSelect
      v-model="form.type"
      label="Tipo"
      :options="TRANSACTION_TYPES"
      :error="errors.type"
      required
    />

    <!-- Monto (always in account currency) -->
    <AmountInput
      v-model="form.amount"
      label="Monto"
      :currency="selectedAccountCurrency"
      placeholder="0.00"
      :error="errors.amount"
      required
    />

    <!-- Título -->
    <BaseInput
      v-model="form.title"
      label="Título (opcional)"
      placeholder="Ej: Compra supermercado"
    />

    <!-- Descripción -->
    <BaseInput
      v-model="form.description"
      label="Descripción (opcional)"
      placeholder="Detalles adicionales"
    />

    <!-- Fecha -->
    <DatePicker
      v-model="form.date"
      label="Fecha"
      :error="errors.date"
      :max="formatDateForInput(new Date())"
      required
    />

    <!-- Cuenta -->
    <AccountSelect
      v-model="form.account_id"
      :accounts="accounts"
      :error="errors.account_id"
      required
    />

    <!-- Categoría (filtered by type) -->
    <CategorySelect
      v-model="form.category_id"
      :categories="categories"
      :filter-type="form.type"
      :error="errors.category_id"
      required
    />

    <!-- ------------------------------------------------------------------ -->
    <!-- Opciones avanzadas (collapsible) -->
    <!-- ------------------------------------------------------------------ -->
    <div class="rounded-lg border border-dark-border bg-dark-bg-secondary overflow-hidden">
      <!-- Section header / toggle -->
      <button
        type="button"
        class="w-full flex items-center justify-between px-4 py-3 text-left min-h-touch hover:bg-dark-bg-tertiary transition-colors"
        :aria-expanded="isAdvancedOpen"
        aria-controls="advanced-section-body"
        @click="isAdvancedOpen = !isAdvancedOpen"
      >
        <span class="text-sm font-medium text-dark-text-secondary">Opciones avanzadas</span>
        <!-- Chevron icon — rotates 180° when open -->
        <svg
          class="w-4 h-4 text-dark-text-tertiary flex-shrink-0 transition-transform duration-200"
          :class="{ 'rotate-180': isAdvancedOpen }"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      <!-- Expandable body -->
      <Transition name="adv-expand">
        <div
          v-if="isAdvancedOpen"
          id="advanced-section-body"
          class="px-4 pb-4 space-y-4 border-t border-dark-border pt-4"
        >
          <!-- Tags -->
          <BaseInput
            v-model="form.tags"
            label="Etiquetas (opcional)"
            placeholder="comida, semanal (separadas por comas)"
            helper-text="Separadas por comas"
          />

          <!-- Moneda extranjera (optional) -->
          <div class="w-full">
            <BaseSelect
              v-model="foreignCurrency"
              label="Moneda extranjera (opcional)"
              :options="foreignCurrencyOptions"
              placeholder="Sin moneda extranjera"
            />
          </div>

          <!-- FX collapsible section (independent inner block) -->
          <div v-if="fxActive" class="rounded-lg border border-dark-border bg-dark-bg-tertiary overflow-hidden">
            <!-- Section header / toggle -->
            <button
              type="button"
              class="w-full flex items-center justify-between px-4 py-3 text-left min-h-touch hover:bg-dark-bg-secondary transition-colors"
              :aria-expanded="isFxSectionOpen"
              aria-controls="fx-section-body"
              @click="isFxSectionOpen = !isFxSectionOpen"
            >
              <span class="text-sm font-medium text-dark-text-secondary">
                Detalle de cambio de divisas
                <span class="ml-1 text-dark-text-tertiary text-xs font-normal">
                  ({{ foreignCurrency }} → {{ selectedAccountCurrency }})
                </span>
              </span>
              <!-- Chevron icon — rotates 180° when open -->
              <svg
                class="w-4 h-4 text-dark-text-tertiary flex-shrink-0 transition-transform duration-200"
                :class="{ 'rotate-180': isFxSectionOpen }"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            <!-- Expandable body -->
            <Transition name="fx-expand">
              <div
                v-if="isFxSectionOpen"
                id="fx-section-body"
                class="px-4 pb-4 space-y-3 border-t border-dark-border"
              >
                <!-- Suggested rate hint (when available) -->
                <p
                  v-if="suggestedRate !== null"
                  class="pt-3 text-xs text-dark-text-tertiary"
                >
                  Tasa sugerida: 1 {{ foreignCurrency }} = {{ formatRate(suggestedRate) }} {{ selectedAccountCurrency }}
                </p>
                <div v-else class="pt-3" />

                <!-- Original amount (in foreign currency) -->
                <div class="w-full">
                  <label class="label">
                    Monto original
                    <span class="ml-1 text-dark-text-tertiary text-xs font-normal">({{ foreignCurrency }})</span>
                    <span class="text-accent-red ml-1">*</span>
                  </label>
                  <input
                    type="number"
                    min="0"
                    step="any"
                    :value="originalAmount ?? ''"
                    inputmode="decimal"
                    placeholder="0.00"
                    class="input"
                    @input="handleOriginalAmountInput"
                  />
                </div>

                <!-- Exchange rate -->
                <div class="w-full">
                  <label class="label">
                    Tasa de cambio
                    <span class="ml-1 text-dark-text-tertiary text-xs font-normal">
                      ({{ selectedAccountCurrency }} por 1 {{ foreignCurrency }})
                    </span>
                    <span class="text-accent-red ml-1">*</span>
                  </label>
                  <input
                    type="number"
                    min="0"
                    step="any"
                    :value="formatRate(exchangeRate)"
                    inputmode="decimal"
                    placeholder="0.00"
                    class="input"
                    @input="handleRateInput"
                  />
                  <!-- Rate deviation alert (Phase 5.2 integrated) -->
                  <div v-if="showRateAlert" class="flex items-center gap-1 text-xs text-yellow-500 dark:text-yellow-400 mt-1">
                    <span>&#x26A0;&#xFE0F;</span>
                    <span>La tasa ingresada difiere más del 10% de la tasa de mercado sugerida</span>
                  </div>
                </div>

                <!-- Amount in account currency (calculated or user-entered) -->
                <div class="w-full">
                  <label class="label">
                    Monto en {{ selectedAccountCurrency }}
                    <span class="text-accent-red ml-1">*</span>
                  </label>
                  <input
                    type="number"
                    min="0"
                    step="any"
                    :value="accountAmount ?? ''"
                    inputmode="decimal"
                    placeholder="0.00"
                    class="input"
                    @input="handleAccountAmountInput"
                  />
                  <p class="mt-1 text-xs text-dark-text-tertiary">
                    Este valor se guarda como el monto de la transacción.
                  </p>
                </div>
              </div>
            </Transition>
          </div>
        </div>
      </Transition>
    </div>

    <!-- Actions -->
    <div class="flex gap-3 pt-4 flex-col md:flex-row">
      <BaseButton
        type="submit"
        variant="primary"
        :loading="loading"
        full-width
      >
        {{ isEditMode ? 'Actualizar' : 'Crear' }} transacción
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

<style scoped>
/* FX section expand/collapse animation.
   Using max-height + opacity for a smooth "accordion" feel.
   max-height is set high enough to never clip real content on mobile. */
.fx-expand-enter-active,
.fx-expand-leave-active {
  transition: max-height 0.25s ease, opacity 0.2s ease;
  overflow: hidden;
  max-height: 500px;
}

.fx-expand-enter-from,
.fx-expand-leave-to {
  max-height: 0;
  opacity: 0;
}

/* Advanced options section — same accordion pattern as FX.
   max-height is larger to accommodate all optional fields. */
.adv-expand-enter-active,
.adv-expand-leave-active {
  transition: max-height 0.25s ease, opacity 0.2s ease;
  overflow: hidden;
  max-height: 900px;
}

.adv-expand-enter-from,
.adv-expand-leave-to {
  max-height: 0;
  opacity: 0;
}
</style>
